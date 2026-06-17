/* Editor de Mapa "Mapas FAI" — MapLibre GL JS + Terra Draw. NORTE SEMPRE PARA CIMA.
   ----------------------------------------------------------------------------
   - Sem rotação (bearing=0): mapa, folha A3 e PDF norte-acima (terreno reto).
   - O #map tem proporção A3; ao "Fechar mapa" a folha PREENCHE o quadro e só ela
     fica acessível (setMaxBounds + setMinZoom).
   - Enquanto se POSICIONA (antes de fechar), a folha ACOMPANHA o centro da vista
     (conserta o bug de ela ficar travada na região de origem); com pontos, ela
     auto-enquadra o bounding box dos pontos.
   - Terra Draw desenha áreas/rota; pontos são gerenciados aqui (círculo + rótulo
     ao lado, FORA do círculo + anel do raio). Resto do app continua em Leaflet.
   Contrato de dados IDÊNTICO (coords [lat,lon]; GeoJSON do Terra Draw é [lng,lat]). */

const TYPECOL = {SP:'#15803d', FP:'#b91c1c', TP:'#2f6df0', HG:'#7a52c4', TG:'#d97706'};
const AREACOL = {proibida:'#e53935', atencao:'#f9a825', livre:'#2e9e4f'};
const BASE_LBL = {esri:'Satélite', topo:'Topográfico', osm:'OpenStreetMap'};
const $ = (s)=>document.querySelector(s);

let map, draw, drawReady = false;
let points = [], frame = null, captured = false, loading = true, dirty = false, saveTimer = null;
let tool = 'idle', pointMode = false;
let undoStack = [], redoStack = [];
let areaKinds = {};        // featureId (Terra Draw) -> 'proibida'|'atencao'|'livre'
let markers = [];          // marcadores MapLibre dos pontos
let selectedId = null;     // forma selecionada no Terra Draw
let folhaSvg = null;

function uid(){return Math.random().toString(36).slice(2,8);}
function esc(s){const d=document.createElement('div');d.textContent=String(s==null?'':s);return d.innerHTML;}
function curSlug(){return (window.MAPA_INIT&&window.MAPA_INIT.mapa&&window.MAPA_INIT.mapa.slug)||'';}

/* ---------- estilo MapLibre (3 bases raster; alterna por visibilidade) ---------- */
function baseStyle(){
  return {
    version: 8,
    sources: {
      topo: {type:'raster', tiles:['https://a.tile.opentopomap.org/{z}/{x}/{y}.png','https://b.tile.opentopomap.org/{z}/{x}/{y}.png'], tileSize:256, maxzoom:17, attribution:'© OpenTopoMap'},
      esri: {type:'raster', tiles:['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'], tileSize:256, maxzoom:19, attribution:'Imagery © Esri'},
      osm:  {type:'raster', tiles:['https://a.tile.openstreetmap.org/{z}/{x}/{y}.png','https://b.tile.openstreetmap.org/{z}/{x}/{y}.png'], tileSize:256, maxzoom:19, attribution:'© OpenStreetMap'}
    },
    layers: [
      {id:'esri', type:'raster', source:'esri', layout:{visibility:'visible'}},
      {id:'topo', type:'raster', source:'topo', layout:{visibility:'none'}},
      {id:'osm',  type:'raster', source:'osm',  layout:{visibility:'none'}}
    ]
  };
}
function setBase(b){
  b=b||'esri';
  ['topo','esri','osm'].forEach(id=>{ if(map.getLayer(id)) map.setLayoutProperty(id,'visibility', id===b?'visible':'none'); });
  const lbl=$('#layersLbl'); if(lbl) lbl.textContent=BASE_LBL[b]||'Base';
}

/* ---------- proporção A3 do quadro do mapa (container exatamente A3 → folha preenche) ---------- */
function applyMapAspect(){
  const box=$('#mapBox'), wrap=$('#mapWrap'); if(!box||!wrap) return;
  const ratio = ($('#mOrient').value==='retrato') ? 297/420 : 420/297;   // w/h
  const availW = box.clientWidth || 900;
  const availH = Math.max(360, window.innerHeight*0.80);
  let w = availW, h = w/ratio;
  if(h>availH){ h=availH; w=h*ratio; }
  wrap.style.width = Math.floor(w)+'px';
  wrap.style.height = Math.floor(h)+'px';
  if(map){ setTimeout(()=>{ map.resize(); if(captured) fitToFrame(); else drawFolha(); }, 30); }
}

function init(){
  applyMapAspect();
  map = new maplibregl.Map({
    container:'map', style:baseStyle(), center:[-46.8,-24.18], zoom:11,
    dragRotate:true, pitchWithRotate:false, attributionControl:{compact:true}
  });
  // rotação LIVRE ao posicionar (seleção em ângulo); a bússola mostra/zera o norte
  map.addControl(new maplibregl.NavigationControl({showCompass:true, visualizePitch:false}), 'bottom-right');

  // Etapa 1
  $('#mBase').onchange=()=>setBase($('#mBase').value);
  $('#fFrameColor').onchange=drawFolha;
  $('#mScale').onchange=()=>{ syncMirrors(); refreshFrame(); };
  $('#mOrient').onchange=()=>{ syncMirrors(); applyMapAspect(); refreshFrame(); };
  $('#bCreate').onclick=closeMap;

  // busca
  $('#searchBtn').onclick=()=>doSearch();
  $('#searchBox').addEventListener('input', onSearchInput);
  $('#searchBox').addEventListener('keydown', e=>{ if(e.key==='Enter'){e.preventDefault(); const f=$('#searchResults button'); if(f) f.click(); else doSearch();} else if(e.key==='Escape') hideResults(); });
  document.addEventListener('click', e=>{ if(!e.target.closest('#searchForm')) hideResults(); });

  // Etapa 2 — barra (1 linha, sem rotação/base/nav)
  $('#bReopen').onclick=reopenMap;
  $('#tDelShape').onclick=delSelected;
  $('#tPoint').onclick=()=>toggleTool('point');
  $('#tPoly').onclick=()=>toggleTool('polygon');
  $('#tRect').onclick=()=>toggleTool('rectangle');
  $('#tCirc').onclick=()=>toggleTool('circle');
  $('#tRoute').onclick=()=>toggleTool('linestring');
  $('#tUndo').onclick=undo; $('#tRedo').onclick=redo;
  $('#bSave').onclick=()=>save(false); $('#bPublish').onclick=()=>save(true);
  $('#bPreview').onclick=(e)=>{ e.preventDefault(); const b=$('#mBase').value; save(false, slug=>window.open('/mapas/'+encodeURIComponent(slug)+'/mapa.pdf?base='+encodeURIComponent(b),'_blank')); };  // exporta na base selecionada agora
  ['dName','dStyle','dTeto','dAlt','dOrg','dTit','dData','dLocal'].forEach(id=>{const el=$('#'+id); if(el) el.onchange=markDirty;});
  $('#pRadius').onchange=()=>{const t=$('#pNext').value; points.forEach(p=>{if(p.type===t)p.radius=+$('#pRadius').value;}); render(); markDirty();};
  document.addEventListener('keydown', e=>{ if((e.key==='Delete'||e.key==='Backspace') && selectedId!=null && !/INPUT|SELECT|TEXTAREA/.test((e.target.tagName||''))) { delSelected(); } });
  window.addEventListener('beforeunload', e=>{ if(dirty){e.preventDefault();e.returnValue='';} });
  window.addEventListener('resize', ()=>{ clearTimeout(window.__ar); window.__ar=setTimeout(applyMapAspect,150); });

  // controle de camadas (estilo Google)
  $('#layersThumb').onclick=()=>$('#layersMenu').classList.toggle('d-none');
  document.querySelectorAll('.lay-opt').forEach(b=>b.onclick=()=>{ const v=b.dataset.base; $('#mBase').value=v; setBase(v); $('#layersMenu').classList.add('d-none'); markDirty(); });
  document.addEventListener('click', e=>{ if(!e.target.closest('#layersCtl')) $('#layersMenu').classList.add('d-none'); });

  map.on('load', onMapLoad);
}

function onMapLoad(){
  setBase($('#mBase').value);
  // overlay SVG da folha (borda + recorte só ao posicionar)
  folhaSvg = document.createElementNS('http://www.w3.org/2000/svg','svg');
  folhaSvg.setAttribute('id','folhaSvg');
  // folha = retângulo RETO na tela (captura a faixa girada) + agulha de Norte (estilo AITA) viva
  folhaSvg.innerHTML =
      '<defs><pattern id="nhatch" width="3.5" height="3.5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
    +   '<line x1="0" y1="0" x2="0" y2="3.5" stroke="#111" stroke-width="1"></line></pattern></defs>'
    + '<path id="folhaMask" fill="#0a1722" fill-rule="evenodd"></path>'
    + '<rect id="folhaBox" fill="none"></rect>'
    + '<g id="folhaRose" style="pointer-events:none">'
    +   '<polygon points="0,-26 -11,16 0,6" fill="url(#nhatch)"></polygon>'                 // metade esq. hachurada
    +   '<polygon points="0,-26 11,16 0,6" fill="#ffffff"></polygon>'                        // metade dir. branca
    +   '<polygon points="0,-26 -11,16 0,6 11,16" fill="none" stroke="#111" stroke-width="3" stroke-linejoin="round"></polygon>'
    +   '<text x="0" y="-30" text-anchor="middle" font-size="12" font-weight="800" fill="#111">N</text>'
    + '</g>';
  map.getContainer().appendChild(folhaSvg);

  map.addSource('pt-rings', {type:'geojson', data:emptyFC()});
  map.addLayer({id:'pt-rings-ln', type:'line', source:'pt-rings',
    paint:{'line-color':['get','color'],'line-width':1.4,'line-opacity':0.9}});

  initDraw();

  map.on('move', onMove);
  map.on('rotate', onMove);
  map.on('zoom', drawFolha);
  map.on('resize', drawFolha);
  map.on('click', onMapClick);

  if(window.MAPA_INIT){ loadInit(window.MAPA_INIT); }
  else {
    loading=false;
    const c=map.getCenter(); frame={lat:c.lat, lon:c.lng, angle:0};
    $('#layersCtl').classList.remove('d-none');
    if(navigator.geolocation) navigator.geolocation.getCurrentPosition(
      pos=>{ if(!captured){ map.jumpTo({center:[pos.coords.longitude,pos.coords.latitude], zoom:13}); } },
      ()=>{}, {timeout:6000, maximumAge:600000});
    drawFolha();
  }
  checkDraft();
}

/* a folha acompanha a vista ao posicionar (sem pontos); com pontos, segue o bbox */
function onMove(){
  if(!captured && frame){
    if(!points.length){ const c=map.getCenter(); frame.lat=c.lat; frame.lon=c.lng; }
    frame.angle = map.getBearing();   // a folha acompanha a rotação (captura faixa girada)
  }
  drawFolha();
}
function refreshFrame(){ if(points.length) frameFromPoints(); drawFolha(); }
function frameFromPoints(){
  if(!points.length) return;
  const la=points.map(p=>p.lat), lo=points.map(p=>p.lon);
  if(!frame) frame={angle:0};
  frame.lat=(Math.min(...la)+Math.max(...la))/2; frame.lon=(Math.min(...lo)+Math.max(...lo))/2;
  if(!captured && map) frame.angle=map.getBearing();   // mantém o ângulo da vista (não força norte)
  // aviso se a rota não couber na folha
  const {w,h}=a3dims();
  const gy=(Math.max(...la)-Math.min(...la))*111320, gx=(Math.max(...lo)-Math.min(...lo))*111320*Math.cos(frame.lat*Math.PI/180);
  const info=$('#frameInfo');
  if(info && (gx>w||gy>h)) info.innerHTML='<span class="text-danger">Os pontos não cabem na folha desta escala — escolha uma escala maior.</span>';
}

/* ---------- Terra Draw ---------- */
function initDraw(){
  const TD = window.terraDraw, AD = window.terraDrawMapLibreGLAdapter;
  if(!TD || !AD){ console.error('Terra Draw não carregou (UMD).'); return; }
  const areaFill = (f)=>AREACOL[(f&&areaKinds[f.id])||'proibida'];
  const polyStyles = {fillColor:areaFill, outlineColor:areaFill, fillOpacity:0.22, outlineWidth:2};
  const modes=[]; const add=(fn)=>{ try{ modes.push(fn()); }catch(e){ console.warn('modo Terra Draw indisponível:', e); } };
  add(()=>new TD.TerraDrawPolygonMode({styles:polyStyles}));
  add(()=>new TD.TerraDrawRectangleMode({styles:polyStyles}));
  add(()=>new TD.TerraDrawCircleMode({styles:polyStyles}));
  add(()=>new TD.TerraDrawLineStringMode({styles:{lineStringColor:'#0ea5e9', lineStringWidth:3}}));
  add(()=>new TD.TerraDrawSelectMode({flags:selectFlags()}));
  try{
    draw = new TD.TerraDraw({adapter:new AD.TerraDrawMapLibreGLAdapter({map, lib:maplibregl}), modes});
    draw.start();
    draw.setMode('select');
    draw.on('change', onDrawChange);
    draw.on('finish', ()=>{ snapshot(); updateCounts(); markDirty(); });
    draw.on('select', id=>{ selectedId=id; $('#tDelShape').classList.remove('d-none'); });
    draw.on('deselect', ()=>{ selectedId=null; $('#tDelShape').classList.add('d-none'); });
    drawReady=true;
  }catch(e){ console.error('Terra Draw init falhou:', e); }
}
function selectFlags(){
  const f={feature:{draggable:true, coordinates:{midpoints:true, draggable:true, deletable:true}}};
  return {polygon:f, rectangle:{feature:{draggable:true}}, circle:{feature:{draggable:true}}, linestring:f};
}
function onDrawChange(ids, type){
  if(type==='create' && !loading){   // !loading: não sobrescrever a cor salva ao recarregar/undo (addFeatures dispara 'create')
    const snap = drawSnapshot();
    ids.forEach(id=>{ const ft = snap.find(f=>f.id===id); if(ft && ft.geometry.type==='Polygon') areaKinds[id]=$('#aColor').value; });
  } else if(type==='delete'){
    ids.forEach(id=>{ delete areaKinds[id]; });
    snapshot();
  }
  updateCounts();
}
function drawSnapshot(){ try{ return draw.getSnapshot(); }catch(e){ return []; } }
function delSelected(){
  if(selectedId==null) return;
  try{ draw.removeFeatures([selectedId]); }catch(e){}
  delete areaKinds[selectedId]; selectedId=null; $('#tDelShape').classList.add('d-none');
  snapshot(); updateCounts(); markDirty();
}

/* ---------- folha A3 (norte-acima; caixa upright) ---------- */
function scaleDenom(){return parseInt(($('#mScale').value||'1:50000').split(':')[1],10)||50000;}
function a3dims(){const d=scaleDenom(); const por=$('#mOrient').value==='retrato';
  return por?{w:0.297*d,h:0.420*d}:{w:0.420*d,h:0.297*d};}   // metros de solo
function frameCornersGround(){   // [[lat,lon]] dos 4 cantos da folha, girada por frame.angle (faixa diagonal no solo)
  const {w,h}=a3dims(), a=(frame.angle||0)*Math.PI/180, coslat=Math.cos(frame.lat*Math.PI/180), hw=w/2, hh=h/2;
  return [[-hw,-hh],[hw,-hh],[hw,hh],[-hw,hh]].map(([dx,dy])=>{
    const e=dx*Math.cos(a)-dy*Math.sin(a), n=dx*Math.sin(a)+dy*Math.cos(a);
    return [frame.lat+n/111320, frame.lon+e/(111320*coslat)];
  });
}
function frameColor(){ const el=$('#fFrameColor'); return (el&&el.value)||'#e53935'; }
function metersPerPixel(){
  if(!frame) return 1;
  const a=map.project([frame.lon, frame.lat]);
  const b=map.project([frame.lon, frame.lat+0.001]);
  const dpx=Math.hypot(b.x-a.x, b.y-a.y) || 1;
  return (0.001*111320)/dpx;
}
function drawFolha(){
  if(!folhaSvg) return;
  const cont=map.getContainer(); const W=cont.clientWidth, H=cont.clientHeight;
  folhaSvg.setAttribute('width',W); folhaSvg.setAttribute('height',H);
  folhaSvg.setAttribute('viewBox','0 0 '+W+' '+H);
  const mask=$('#folhaMask'), box=$('#folhaBox'), rose=$('#folhaRose');
  if(!frame){ if(mask)mask.setAttribute('d',''); if(box)box.setAttribute('width',0); if(rose)rose.setAttribute('transform','translate(-99,-99)'); return; }
  // folha = retângulo RETO na tela (centro projetado ± meia-folha); captura a faixa girada no solo
  const mpp=metersPerPixel(); const {w,h}=a3dims();
  const c=map.project([frame.lon, frame.lat]);
  const hw=(w/2)/mpp, hh=(h/2)/mpp;
  const x0=c.x-hw, y0=c.y-hh, x1=c.x+hw, y1=c.y+hh;
  // escurece fora da folha SÓ ao posicionar (fechado: bounds travados, nada fora)
  mask.setAttribute('d', captured ? '' : `M0,0 H${W} V${H} H0 Z M${x0},${y0} H${x1} V${y1} H${x0} Z`);
  mask.setAttribute('opacity', 0.42);
  box.setAttribute('x',x0); box.setAttribute('y',y0);
  box.setAttribute('width',Math.max(0,x1-x0)); box.setAttribute('height',Math.max(0,y1-y0));
  box.setAttribute('stroke', frameColor()); box.setAttribute('stroke-width', captured?1.5:2.5);
  // agulha de Norte no canto INFERIOR-DIREITO da folha (fora da barra de ferramentas), apontando o NORTE
  const rx=Math.min(x1,W)-34, ry=Math.min(y1,H)-40;
  rose.setAttribute('transform', `translate(${rx.toFixed(1)},${ry.toFixed(1)}) rotate(${(-map.getBearing()).toFixed(1)})`);
  const info=$('#frameInfo'); if(info && !captured && !points.length) info.innerHTML=`A3 ${$('#mOrient').value} ${esc($('#mScale').value)} — <b>${(w/1000).toFixed(1)}×${(h/1000).toFixed(1)} km</b> · gire a vista; a rosa aponta o norte`;
}

/* ---------- Fechar / Reabrir ---------- */
function frameBoundsLngLat(){
  const cs=frameCornersGround();
  let minLa=90,maxLa=-90,minLo=180,maxLo=-180;
  cs.forEach(([la,lo])=>{minLa=Math.min(minLa,la);maxLa=Math.max(maxLa,la);minLo=Math.min(minLo,lo);maxLo=Math.max(maxLo,lo);});
  return [[minLo,minLa],[maxLo,maxLa]];
}
function fitToFrame(){
  try{ map.setMaxBounds(null); map.setMinZoom(0); }catch(e){}
  try{
    // enquadra a folha (mantendo o ângulo capturado) calculando o zoom p/ ela preencher o quadro A3
    const cont=map.getContainer(); const cw=cont.clientWidth||1, ch=cont.clientHeight||1;
    const {w,h}=a3dims(); const mpp=metersPerPixel();
    const target=Math.max(w/cw, h/ch);           // metros por pixel para a folha caber
    const dz=Math.log2((mpp||target)/target);
    map.jumpTo({center:[frame.lon, frame.lat], bearing:(frame.angle||0), zoom:map.getZoom()+dz});
    const z=map.getZoom();
    map.setMaxBounds(frameBoundsLngLat());        // bbox dos cantos girados (permite leve pan)
    map.setMinZoom(Math.max(0, z-0.05));
  }catch(e){}
  setTimeout(drawFolha, 60);
}
function closeMap(){
  if(!loading && !$('#mName').value.trim()){ alert('Dê um nome ao mapa.'); return; }  // !loading: não bloqueia ao carregar/restaurar
  if(!frame){ const c=map.getCenter(); frame={lat:c.lat,lon:c.lng,angle:0}; }
  if(points.length) frameFromPoints();
  captured=true;
  try{ frame.angle=map.getBearing(); map.dragRotate.disable(); }catch(e){}   // mantém o ângulo capturado (faixa girada); só trava a rotação
  $('#dName').value=$('#mName').value; $('#dScale').value=$('#mScale').value;
  $('#dOrient').value=$('#mOrient').value==='retrato'?'Retrato':'Paisagem';
  $('#dTeto').value=$('#mTeto').value; $('#dAlt').value=$('#mAlt').value;
  $('#dOrg').value=$('#mOrg').value; $('#dTit').value=$('#mTit').value; $('#dData').value=$('#mData').value; $('#dLocal').value=$('#mLocal').value;
  $('#createPanel').classList.add('d-none'); $('#dataPanel').classList.remove('d-none');
  $('#toolbar').classList.remove('d-none'); $('#layersCtl').classList.remove('d-none');
  setTool('idle');
  if(curSlug()){ $('#bPreview').href='/mapas/'+encodeURIComponent(curSlug())+'/mapa.pdf'; $('#bPreview').classList.remove('disabled'); }
  $('#hint').textContent='Norte para cima. Adicione pontos/áreas. Zoom livre para precisão. ↩ para reposicionar.';
  loading=false; fitToFrame(); snapshot(); updateCounts();
}
function reopenMap(){
  captured=false;
  try{ map.setMaxBounds(null); map.setMinZoom(0); map.dragRotate.enable(); }catch(e){}   // volta a poder girar (seleção em ângulo)
  // devolve edições do painel p/ a etapa de config
  $('#mName').value=$('#dName').value||$('#mName').value;
  $('#mTeto').value=$('#dTeto').value||$('#mTeto').value; $('#mAlt').value=$('#dAlt').value||$('#mAlt').value;
  $('#mOrg').value=$('#dOrg').value; $('#mTit').value=$('#dTit').value; $('#mData').value=$('#dData').value; $('#mLocal').value=$('#dLocal').value;
  $('#dataPanel').classList.add('d-none'); $('#createPanel').classList.remove('d-none');
  $('#toolbar').classList.add('d-none');
  setTool('idle');
  $('#hint').textContent='Reposicione: a folha acompanha a vista (ou os pontos). Depois clique "Fechar mapa".';
  drawFolha();
}

/* ---------- ferramentas (toggle; sem botões mover/selecionar/lixeira fixos) ---------- */
function toggleTool(t){ setTool(tool===t ? 'idle' : t); }
function setTool(t){
  tool=t; pointMode=(t==='point');
  if(drawReady){
    try{
      if(t==='idle'||t==='point') draw.setMode('select');
      else draw.setMode(t);  // polygon / rectangle / circle / linestring
    }catch(e){}
  }
  const navTool=(t==='idle'||t==='point');
  if(map){ if(navTool) map.dragPan.enable(); else map.dragPan.disable(); }
  [['tPoint','point'],['tPoly','polygon'],['tRect','rectangle'],['tCirc','circle'],['tRoute','linestring']]
    .forEach(([id,v])=>{const el=$('#'+id); if(el) el.classList.toggle('active', t===v);});
}

/* ---------- pontos ---------- */
function nextName(type){
  if(type==='SP')return 'SP'; if(type==='FP')return 'FP';
  if(type==='TP')return String(points.filter(p=>p.type==='TP').length+1);
  if(type==='HG')return 'FXC'+String(points.filter(p=>p.type==='HG').length+1).padStart(3,'0');
  if(type==='TG')return 'TG'+String(points.filter(p=>p.type==='TG').length+1);
  return type;
}
function onMapClick(e){
  if(!pointMode || tool!=='point') return;
  const type=$('#pNext').value;
  if((type==='SP'||type==='FP') && points.some(p=>p.type===type)){ alert('Já existe um '+type+'.'); return; }
  points.push({id:uid(),name:nextName(type),type,radius:+$('#pRadius').value||200,lat:e.lngLat.lat,lon:e.lngLat.lng});
  if(type==='SP') $('#pNext').value='TP';
  if(!captured) frameFromPoints();
  snapshot(); markDirty(); render();
}
function circleToPoly(lat0,lon0,r){
  const mLat=111320, mLon=111320*Math.cos(lat0*Math.PI/180), out=[];
  for(let i=0;i<36;i++){const a=i/36*2*Math.PI; out.push([lat0+(r*Math.sin(a))/mLat, lon0+(r*Math.cos(a))/mLon]);}
  return out;
}
function emptyFC(){return {type:'FeatureCollection', features:[]};}
function ringsFC(){
  return {type:'FeatureCollection', features: points.map(p=>{
    const ring=circleToPoly(p.lat,p.lon,+p.radius||1).map(([la,lo])=>[lo,la]); ring.push(ring[0]);
    return {type:'Feature', properties:{color:TYPECOL[p.type]||'#888'}, geometry:{type:'Polygon', coordinates:[ring]}};
  })};
}
function render(){
  if(map.getSource('pt-rings')) map.getSource('pt-rings').setData(ringsFC());
  markers.forEach(m=>m.remove()); markers=[];
  points.forEach(p=>{
    const el=document.createElement('div'); el.className='wp-pt'; el.style.setProperty('--c', TYPECOL[p.type]||'#888');
    el.innerHTML='<span class="wp-dot"></span><span class="wp-name">'+esc(p.name)+'</span>';  // número FORA do círculo
    const m=new maplibregl.Marker({element:el, draggable:true, anchor:'center'}).setLngLat([p.lon,p.lat]).addTo(map);
    m.on('dragend',()=>{const ll=m.getLngLat(); p.lat=ll.lat; p.lon=ll.lng; if(map.getSource('pt-rings'))map.getSource('pt-rings').setData(ringsFC()); if(!captured) frameFromPoints(); snapshot(); markDirty();});
    markers.push(m);
  });
  renderTable(); updateCounts();
}
function renderTable(){
  const tb=$('#ptTable tbody'); if(!tb) return; tb.innerHTML='';
  points.forEach((p,i)=>{
    const tr=document.createElement('tr');
    const tdN=document.createElement('td'); tdN.textContent=i+1;
    const tdName=document.createElement('td'); const inName=document.createElement('input');
    inName.className='form-control form-control-sm'; inName.style.width='56px'; inName.value=p.name;
    inName.onchange=()=>{p.name=inName.value;snapshot();markDirty();render();}; tdName.appendChild(inName);
    const tdType=document.createElement('td'); const sel=document.createElement('select'); sel.className='form-select form-select-sm';
    ['SP','TP','HG','TG','FP'].forEach(t=>{const o=document.createElement('option');o.value=t;o.textContent=t;if(t===p.type)o.selected=true;sel.appendChild(o);});
    sel.onchange=()=>{p.type=sel.value;snapshot();markDirty();render();}; tdType.appendChild(sel);
    const tdR=document.createElement('td'); const inRad=document.createElement('input'); inRad.type='number';
    inRad.className='form-control form-control-sm'; inRad.style.width='56px'; inRad.value=p.radius;
    inRad.onchange=()=>{p.radius=+inRad.value;snapshot();markDirty();render();}; tdR.appendChild(inRad);
    const tdD=document.createElement('td'); const b=document.createElement('button'); b.className='btn btn-sm btn-outline-danger py-0'; b.textContent='×';
    b.onclick=()=>{points.splice(i,1);if(!captured)frameFromPoints();snapshot();markDirty();render();}; tdD.appendChild(b);
    tr.append(tdN,tdName,tdType,tdR,tdD); tb.appendChild(tr);
  });
}

/* ---------- coletar áreas/rota do Terra Draw ---------- */
function collect(){
  const areas=[]; let route={};
  drawSnapshot().forEach(ft=>{
    const g=ft.geometry;
    if(g.type==='Polygon'){
      const ring=(g.coordinates[0]||[]).slice();
      if(ring.length>1 && ring[0][0]===ring[ring.length-1][0] && ring[0][1]===ring[ring.length-1][1]) ring.pop();
      if(ring.length>=3) areas.push({kind:areaKinds[ft.id]||'proibida', name:'', coords:ring.map(c=>[c[1],c[0]])});
    } else if(g.type==='LineString'){
      const ll=g.coordinates||[]; if(ll.length>=2) route={coords:ll.map(c=>[c[1],c[0]]), width:300};
    }
  });
  return {areas, route};
}
function updateCounts(){
  const g=collect(); $('#cPts').textContent=points.length; $('#cAreas').textContent=g.areas.length;
  if(points.length>=2){ const la=points.map(p=>p.lat),lo=points.map(p=>p.lon);
    const dy=(Math.max(...la)-Math.min(...la))*111.32, dx=(Math.max(...lo)-Math.min(...lo))*111.32*Math.cos(points[0].lat*Math.PI/180);
    $('#autoCalc').textContent=`extensão ~ ${dx.toFixed(1)}×${dy.toFixed(1)} km · ${points.length} pts`;
  } else $('#autoCalc').textContent='—';
}

/* ---------- undo/redo ---------- */
function curState(){const g=collect(); return JSON.stringify({points:points.map(p=>({name:p.name,type:p.type,radius:p.radius,lat:p.lat,lon:p.lon})),areas:g.areas,route:g.route});}
function snapshot(){ if(loading)return; const s=curState(); if(undoStack[undoStack.length-1]===s) return; undoStack.push(s); if(undoStack.length>40)undoStack.shift(); redoStack=[]; }
function applyState(s){
  const d=JSON.parse(s);
  points=(d.points||[]).map(p=>({id:uid(),...p}));
  loadShapes(d.areas||[], d.route||{});
  if(!captured) frameFromPoints();
  render(); drawFolha();   // mantém a folha/máscara em sincronia após undo/redo (inclusive fechado)
}
function loadShapes(areas, route){
  if(!drawReady) return;
  try{ draw.clear(); }catch(e){}
  areaKinds={};
  const feats=[], kinds=[];
  (areas||[]).forEach(a=>{
    const ring=(a.coords||[]).map(([la,lo])=>[lo,la]); if(ring.length<3) return;
    if(ring[0][0]!==ring[ring.length-1][0] || ring[0][1]!==ring[ring.length-1][1]) ring.push(ring[0]);
    feats.push({type:'Feature', properties:{mode:'polygon'}, geometry:{type:'Polygon', coordinates:[ring]}});
    kinds.push(a.kind||'proibida');
  });
  if(route && (route.coords||[]).length>=2){
    feats.push({type:'Feature', properties:{mode:'linestring'}, geometry:{type:'LineString', coordinates:route.coords.map(([la,lo])=>[lo,la])}});
    kinds.push(null);
  }
  if(feats.length){
    try{
      const res=draw.addFeatures(feats);
      (res||[]).forEach((r,i)=>{ const id=(r&&r.id!=null)?r.id:r; if(kinds[i] && id!=null) areaKinds[id]=kinds[i]; });
    }catch(e){ console.warn('addFeatures', e); }
  }
}
function undo(){ if(undoStack.length<2)return; redoStack.push(undoStack.pop()); const w=loading; loading=true; applyState(undoStack[undoStack.length-1]); loading=w; }
function redo(){ if(!redoStack.length)return; const s=redoStack.pop(); undoStack.push(s); const w=loading; loading=true; applyState(s); loading=w; }

/* ---------- busca (Nominatim) ---------- */
let searchTimer=null;
function onSearchInput(){ clearTimeout(searchTimer); const q=$('#searchBox').value.trim(); if(q.length<3){hideResults();return;} searchTimer=setTimeout(()=>fetchSuggest(q),300); }
function fetchSuggest(q){
  fetch('https://nominatim.openstreetmap.org/search?format=json&limit=5&addressdetails=1&q='+encodeURIComponent(q),{headers:{'Accept':'application/json'}})
    .then(r=>r.json()).then(showResults).catch(()=>hideResults());
}
function showResults(list){
  const box=$('#searchResults'); if(!box) return; box.innerHTML='';
  if(!list||!list.length){ hideResults(); return; }
  list.forEach(it=>{
    const a=document.createElement('button'); a.type='button';
    a.className='list-group-item list-group-item-action py-1 small text-truncate';
    a.textContent=it.display_name; a.title=it.display_name;
    a.onclick=()=>{ map.flyTo({center:[+it.lon,+it.lat], zoom:13}); $('#searchBox').value=it.display_name.split(',')[0]; hideResults(); };
    box.appendChild(a);
  });
  box.classList.remove('d-none');
}
function hideResults(){ const b=$('#searchResults'); if(b){b.classList.add('d-none'); b.innerHTML='';} }
function doSearch(){ const q=$('#searchBox').value.trim(); if(q) fetchSuggest(q); }

/* ---------- salvar ---------- */
function syncMirrors(){ if($('#dScale'))$('#dScale').value=$('#mScale').value; if($('#dOrient'))$('#dOrient').value=$('#mOrient').value==='retrato'?'Retrato':'Paisagem'; }
function mapaObj(){
  const g=collect();
  return {mapa:{name:$('#dName').value||$('#mName').value, slug:curSlug(),
      scale:$('#mScale').value, orientation:$('#mOrient').value, base:$('#mBase').value, style:($('#dStyle')?$('#dStyle').value:'pontos'),
      teto:+($('#dTeto').value||$('#mTeto').value||0), alturaMin:+($('#dAlt').value||$('#mAlt').value||0),
      logo:(window.MAPA_INIT&&window.MAPA_INIT.mapa)?(window.MAPA_INIT.mapa.logo||''):'',
      organizador:$('#dOrg').value, titulo:$('#dTit').value, local:$('#dLocal').value, data:$('#dData').value,
      declinacao:($('#mDecl')?$('#mDecl').value:'')},
    points: points.map(p=>({name:p.name,type:p.type,radius:+p.radius,weight:1,lat:p.lat,lon:p.lon,alt:0})),
    areas: g.areas, frame: frame? {lat:frame.lat,lon:frame.lon,angle:(frame.angle||0)} : {}, route: g.route, landings: []};
}
function save(publish, onOk){
  if(!frame){ $('#saveMsg').innerHTML='<span class="text-danger">Defina a folha antes de salvar.</span>'; return; }
  const obj=mapaObj(); if(publish) obj.mapa.publish=true;
  $('#saveMsg').textContent='Salvando…';
  fetch('/mapas/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(obj)})
    .then(r=>r.json()).then(d=>{
      if(!d.ok){ $('#saveMsg').innerHTML='<span class="text-danger">'+esc(d.error||'Erro.')+'</span>'; return; }
      clearDraft();
      window.MAPA_INIT=window.MAPA_INIT||{mapa:{}}; window.MAPA_INIT.mapa=window.MAPA_INIT.mapa||{};
      const wasNew = window.MAPA_INIT.mapa.slug!==d.slug;
      window.MAPA_INIT.mapa.slug=d.slug;
      $('#bPreview').classList.remove('disabled'); $('#bPreview').href='/mapas/'+encodeURIComponent(d.slug)+'/mapa.pdf';
      if(onOk){ onOk(d.slug); }
      const tag = publish ? ' <span class="badge text-bg-success">✔ publicado</span>' : '';
      $('#saveMsg').innerHTML='<span class="text-success">Salvo: <b>'+esc(d.slug)+'</b>.</span>'+tag+' · <a href="/mapas/'+encodeURIComponent(d.slug)+'/mapa.pdf" target="_blank">A3 PDF</a> · <a href="/builder">criar prova</a>';
      if(wasNew){ try{history.replaceState(null,'','/mapas/'+encodeURIComponent(d.slug));}catch(e){} }
    }).catch(()=>$('#saveMsg').innerHTML='<span class="text-danger">Erro ao salvar.</span>');
}

/* ---------- rascunho ---------- */
function draftKey(){return 'aeronav:mapa:'+(curSlug()||'new');}
function markDirty(){ if(loading)return; dirty=true; clearTimeout(saveTimer); saveTimer=setTimeout(()=>{try{localStorage.setItem(draftKey(),JSON.stringify({d:mapaObj()}));}catch(e){}},800); }
function clearDraft(){ try{localStorage.removeItem(draftKey());}catch(e){} dirty=false; }
function checkDraft(){
  let raw; try{raw=localStorage.getItem(draftKey());}catch(e){}
  if(!raw) return;
  $('#draftBar').classList.remove('d-none');
  $('#draftRestore').onclick=ev=>{ev.preventDefault(); try{loadInit(JSON.parse(raw).d);dirty=true;}catch(e){} $('#draftBar').classList.add('d-none');};
  $('#draftDiscard').onclick=ev=>{ev.preventDefault(); clearDraft(); $('#draftBar').classList.add('d-none');};
}

/* ---------- carregar mapa existente / rascunho ---------- */
function loadInit(d){
  loading=true; d=d||{mapa:{}}; const m=d.mapa||{};
  if(m.name){$('#mName').value=m.name;} if(m.scale)$('#mScale').value=m.scale;
  if(m.orientation)$('#mOrient').value=m.orientation; if(m.base){$('#mBase').value=m.base; setBase(m.base);}
  $('#mTeto').value=m.teto||1500; $('#mAlt').value=m.alturaMin||m.altura_min||50;
  $('#mOrg').value=m.organizador||''; $('#mTit').value=m.titulo||''; $('#mData').value=m.data||''; $('#mLocal').value=m.local||'';
  if($('#mDecl')) $('#mDecl').value=m.declinacao||'';
  if($('#dStyle')&&m.style)$('#dStyle').value=m.style;
  syncMirrors(); applyMapAspect();
  $('#layersCtl').classList.remove('d-none');
  points=(d.points||[]).map(p=>({id:uid(),name:p.name,type:p.type,radius:p.radius,lat:p.lat,lon:p.lon}));
  frame=(d.frame&&d.frame.lat)?{lat:d.frame.lat,lon:d.frame.lon,angle:(d.frame.angle||0)}:null;
  if(!frame && points.length){ frame={angle:0}; frameFromPoints(); }
  loadShapes(d.areas||[], d.route||{});
  if(frame){
    map.jumpTo({center:[frame.lon,frame.lat], zoom:13, bearing:(frame.angle||0)});  // reabre no ângulo salvo
    closeMap();   // entra fechado, mantendo o ângulo capturado (faixa girada)
  } else { drawFolha(); loading=false; }
  render();
}

document.addEventListener('DOMContentLoaded', init);
