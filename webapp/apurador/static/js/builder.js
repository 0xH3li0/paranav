/* Construtor de Prova — editor sobre satélite (Esri) + OSM/Topo.
   UI condicional ao tipo (n1/n2/n3), criação de pontos por seletor,
   rascunho automático (localStorage), validação e exportação KML/JSON. */
const TYPECOL = {SP:'#15803d', FP:'#b91c1c', TP:'#2f6df0', HG:'#7a52c4', TG:'#d97706'};
const POINT_TYPES_BY = {n1:['SP','TP','FP'], n2:['SP','TP','HG','TG','FP'], n3:['SP','FP']};
const TYPE_HELP = {
  n1:'Navegação Pura: SP + turnpoints (TP) + FP. Use os Anéis de peso.',
  n2:'Tempo Declarado: SP/TP/FP + hidden gates (HG) e time gates (TG).',
  n3:'Navegação em Curva: SP, FP e a rota/corredor curvo (desenhe a rota).'};
const $ = (s)=>document.querySelector(s);

let map, ptLayer, areaLayer, ringLayer, tmpLayer, frameLayer, routeLayer, landLayer;
let points = [];   // {id,name,type,radius,weight,lat,lon}
let areas = [];    // {kind,name,coords:[[lat,lon]],_p}
let frame = null;  // folha A3: {lat,lon,angle}
let route = null;  // N3: {coords:[[lat,lon]], width}
let landings = []; // pousos: {id,name,lat,lon}
let mode = 'point';
let tmpVerts = [];
let loading = true;        // suprime "dirty"/autosave durante carregamento
let dirty = false;
let saveTimer = null;
let suppressClick = false; // evita criar ponto ao clicar p/ remover área

function uid(){return Math.random().toString(36).slice(2,8);}
function provaType(){return $('#pType').value;}
function R(type){
  const t=provaType();
  if(t==='n1'||t==='n3') return +$('#pRsp').value;            // raio único (n1: todos; n3: SP/FP)
  return (type==='SP'||type==='FP') ? +$('#pRsp').value : +$('#pRin').value;
}
function esc(s){const d=document.createElement('div');d.textContent=String(s==null?'':s);return d.innerHTML;}
function xmlEsc(s){return String(s==null?'':s).replace(/[<>&'"]/g,c=>({'<':'&lt;','>':'&gt;','&':'&amp;',"'":'&apos;','"':'&quot;'}[c]));}
function haversine(a,b){const Rk=6371000,t=x=>x*Math.PI/180;const dLa=t(b[0]-a[0]),dLo=t(b[1]-a[1]);
  const s=Math.sin(dLa/2)**2+Math.cos(t(a[0]))*Math.cos(t(b[0]))*Math.sin(dLo/2)**2;return 2*Rk*Math.asin(Math.min(1,Math.sqrt(s)));}

/* Polígono do corredor (N3): offset perpendicular ±halfM da linha-centro. */
function corridorPolygon(coords, halfM){
  if(!coords || coords.length<2) return null;
  const lat0=coords[0][0], lon0=coords[0][1];
  const mLat=111320, mLon=111320*Math.cos(lat0*Math.PI/180);
  const xy=coords.map(c=>[(c[1]-lon0)*mLon,(c[0]-lat0)*mLat]);
  const left=[], right=[];
  for(let i=0;i<xy.length;i++){
    const p=xy[Math.max(0,i-1)], n=xy[Math.min(xy.length-1,i+1)];
    let dx=n[0]-p[0], dy=n[1]-p[1]; const L=Math.hypot(dx,dy)||1; dx/=L; dy/=L;
    left.push([xy[i][0]-dy*halfM, xy[i][1]+dx*halfM]);
    right.push([xy[i][0]+dy*halfM, xy[i][1]-dx*halfM]);
  }
  return left.concat(right.reverse()).map(q=>[lat0+q[1]/mLat, lon0+q[0]/mLon]);
}
function vertexIcon(color){
  return L.divIcon({className:'', iconSize:[14,14], iconAnchor:[7,7],
    html:`<div style="width:10px;height:10px;border:2px solid ${color};background:#fff;border-radius:50%"></div>`});
}

function init(){
  map = L.map('map').setView([-22.85,-42.55], 12);
  const esri = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    {maxZoom:19, attribution:'Imagery © Esri'}).addTo(map);
  const osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap'});
  const topo = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',{maxZoom:17,attribution:'© OpenTopoMap'});
  L.control.layers({'Satélite (Esri)':esri,'OpenStreetMap':osm,'OpenTopoMap':topo}).addTo(map);
  frameLayer=L.layerGroup().addTo(map); ringLayer=L.layerGroup().addTo(map); areaLayer=L.layerGroup().addTo(map);
  routeLayer=L.layerGroup().addTo(map); landLayer=L.layerGroup().addTo(map);
  ptLayer=L.layerGroup().addTo(map); tmpLayer=L.layerGroup().addTo(map);
  window._previewLayer=L.layerGroup().addTo(map);

  map.on('click', onClick);
  map.on('dblclick', e=>{ if(mode==='proib'||mode==='aten'){ L.DomEvent.stop(e); finishArea(); }
    else if(mode==='route'){ L.DomEvent.stop(e); setMode('point'); }});

  $('#mPoint').onclick=()=>setMode('point'); $('#mProib').onclick=()=>setMode('proib'); $('#mAten').onclick=()=>setMode('aten');
  $('#mRoute').onclick=()=>setMode('route'); $('#mLand').onclick=()=>setMode('pouso');
  $('#rWidth').onchange=()=>{ if(route){route.width=+$('#rWidth').value||300; renderRoute();} markDirty(); };
  $('#bRouteClear').onclick=()=>{ route=null; renderRoute(); markDirty(); };
  $('#bGates').onclick=genGates; $('#bRings').onclick=toggleRings; $('#bRenum').onclick=renumberTPs;
  $('#bClear').onclick=()=>{if(confirm('Limpar tudo?')){points=[];areas=[];route=null;landings=[];markDirty();render();renderRoute();}};
  $('#bSave').onclick=()=>save(false); $('#bSaveAs').onclick=()=>save(true);
  $('#bKml').onclick=exportKML; $('#bJson').onclick=exportJSON;
  $('#loadProva').onchange=e=>{ if(dirty && !confirm('Há mudanças não salvas. Sair mesmo assim?')){e.target.value=(window.PROVA_INIT&&window.PROVA_INIT.prova.slug)||'';return;}
    location.href = e.target.value ? '/builder/'+e.target.value : '/builder'; };
  ['pRsp','pRin'].forEach(id=>$('#'+id).onchange=()=>{points.forEach(p=>p.radius=R(p.type));markDirty();render();});
  ['pName','pTeto','pAlt','pWin'].forEach(id=>$('#'+id).onchange=markDirty);
  $('#pScale').onchange=()=>{drawFrame();markDirty();};
  $('#pType').onchange=onTypeChange;
  $('#pMap').onchange=()=>{ applyMapMode(); markDirty(); };
  $('#bFrame').onclick=toggleFrame;
  $('#fAngle').oninput=()=>{$('#angLbl').textContent=$('#fAngle').value; if(frame){frame.angle=+$('#fAngle').value;drawFrame();markDirty();}};
  $('#searchBtn').onclick=doSearch; $('#searchBox').addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();doSearch();}});
  window.addEventListener('beforeunload', e=>{ if(dirty){ e.preventDefault(); e.returnValue=''; } });

  if(window.PROVA_INIT){ loadInit(window.PROVA_INIT); }
  else {
    loading=false; applyTypeUI();
    // prova nova vinda do modal "Nova Prova" (/builder?map=<slug>): pré-seleciona o mapa.
    const pre=window.PRESELECT_MAP;
    if(pre){ const sel=$('#pMap'); if(sel && [...sel.options].some(o=>o.value===pre)){ sel.value=pre; } }
  }
  applyMapMode();
  checkDraft();
}

/* ---------- modo mapa: a prova puxa a geometria de um Mapa (somente leitura) ---------- */
function mapMode(){ const el=$('#pMap'); return el && el.value; }
function applyMapMode(){
  const slug = mapMode();
  document.querySelectorAll('[data-geom]').forEach(el=>{ el.style.display = slug ? 'none' : ''; });
  const note=$('#mapPreviewNote'), help=$('#mapHelp');
  if(slug){
    if(note){ note.classList.remove('d-none'); note.innerHTML='Geometria do <b>mapa</b> selecionado (somente leitura). Edite no menu <b>Mapas</b>.'; }
    if(help) help.textContent='A prova usa os pontos/áreas/rota deste mapa.';
    loadMapPreview(slug);
  } else {
    if(note) note.classList.add('d-none');
    if(help) help.textContent='Sem mapa: desenhe a geometria aqui (modo legado).';
    window._previewLayer.clearLayers();
    render(); renderRoute();
  }
}
function loadMapPreview(slug){
  // limpa as camadas de edição e mostra um preview não-interativo do mapa
  ptLayer.clearLayers(); areaLayer.clearLayers(); routeLayer.clearLayers(); landLayer.clearLayers();
  const pl=window._previewLayer; pl.clearLayers();
  fetch('/api/mapa/'+encodeURIComponent(slug)+'/mapdata').then(r=>r.json()).then(d=>{
    (d.areas||[]).forEach(a=>{const c=a.kind==='proibida'?'#e53935':(a.kind==='atencao'?'#f9a825':'#2e9e4f');
      if((a.coords||[]).length>=3) L.polygon(a.coords,{color:c,fillColor:c,fillOpacity:.2,weight:2,interactive:false}).addTo(pl);});
    if(d.route && (d.route.coords||[]).length>1)
      L.polyline(d.route.coords,{color:'#0ea5e9',weight:2,dashArray:'6 4',interactive:false}).addTo(pl);
    (d.wpts||[]).forEach(w=>{const col=({SP:'#15803d',FP:'#b91c1c',TP:'#2f6df0',HG:'#7a52c4',TG:'#d97706'})[w.type]||'#888';
      L.circle([w.lat,w.lon],{radius:w.radius,color:col,fillOpacity:.05,weight:1,interactive:false}).addTo(pl);
      L.circleMarker([w.lat,w.lon],{radius:4,color:'#fff',fillColor:col,fillOpacity:1,weight:1,interactive:false})
        .bindTooltip(`${w.name} (${w.type})`).addTo(pl);});
    const pts=(d.wpts||[]).map(w=>[w.lat,w.lon]);
    if(pts.length){try{map.fitBounds(L.latLngBounds(pts).pad(0.2));}catch(e){}}
  }).catch(()=>{});
}

/* ---------- UI condicional ao tipo ---------- */
function rebuildSelect(sel, opts, val){
  sel.innerHTML='';
  opts.forEach(o=>{const op=document.createElement('option');op.value=o;op.textContent=o;sel.appendChild(op);});
  if(val && opts.includes(val)) sel.value=val;
}
function smartNext(allowed){
  if(!points.some(p=>p.type==='SP') && allowed.includes('SP')) return 'SP';
  return allowed.includes('TP') ? 'TP' : allowed[allowed.length-1];
}
function applyTypeUI(){
  const t=provaType();
  document.querySelectorAll('[data-types]').forEach(el=>{
    const ok=el.getAttribute('data-types').split(/\s+/).includes(t);
    el.style.display = ok ? '' : 'none';
  });
  const allowed = POINT_TYPES_BY[t] || ['SP','TP','FP'];
  rebuildSelect($('#pNext'), allowed, smartNext(allowed));
  $('#typeHelp').textContent = TYPE_HELP[t] || '';
  renderTable();
}
function onTypeChange(){
  const t=provaType();
  if(t!=='n2' && points.some(p=>p.type==='HG'||p.type==='TG')
     && confirm('Esta prova tem HG/TG (só valem no N2). Remover esses pontos?'))
    points=points.filter(p=>p.type!=='HG' && p.type!=='TG');
  if(t!=='n3' && route && route.coords.length
     && confirm('Há uma rota/corredor (só vale no N3). Remover a rota?')){ route=null; renderRoute(); }
  applyTypeUI(); markDirty(); render();
}

/* ---------- rascunho (localStorage) ---------- */
function draftKey(){ const slug=(window.PROVA_INIT&&window.PROVA_INIT.prova&&window.PROVA_INIT.prova.slug)||'new'; return 'aeronav:builder:'+slug; }
function markDirty(){
  if(loading) return;
  dirty=true;
  clearTimeout(saveTimer);
  saveTimer=setTimeout(()=>{ try{localStorage.setItem(draftKey(), JSON.stringify({t:Date.now(), data:provaObj()}));}catch(e){} }, 800);
}
function clearDraft(){ try{localStorage.removeItem(draftKey());}catch(e){} dirty=false; }
function checkDraft(){
  let raw; try{raw=localStorage.getItem(draftKey());}catch(e){}
  if(!raw) return;
  $('#draftBar').classList.remove('d-none');
  $('#draftRestore').onclick=ev=>{ev.preventDefault(); try{loadInit(JSON.parse(raw).data); dirty=true;}catch(e){} $('#draftBar').classList.add('d-none');};
  $('#draftDiscard').onclick=ev=>{ev.preventDefault(); clearDraft(); $('#draftBar').classList.add('d-none');};
}

/* ---------- busca de região (Nominatim/OSM) ---------- */
function doSearch(){
  const q=$('#searchBox').value.trim(); if(!q)return;
  fetch('https://nominatim.openstreetmap.org/search?format=json&limit=1&q='+encodeURIComponent(q),{headers:{'Accept':'application/json'}})
    .then(r=>r.json()).then(a=>{ if(a&&a[0]){map.setView([+a[0].lat,+a[0].lon],13);} else alert('Local não encontrado.'); })
    .catch(()=>alert('Busca indisponível.'));
}

/* ---------- folha A3 ---------- */
function scaleDenom(){return parseInt(($('#pScale').value||'1:50000').split(':')[1],10)||50000;}
function a3dims(){const d=scaleDenom();return {w:0.420*d, h:0.297*d};}
function rectCorners(lat,lon,w,h,angDeg){
  const a=angDeg*Math.PI/180, coslat=Math.cos(lat*Math.PI/180);
  const hw=w/2, hh=h/2;
  return [[-hw,-hh],[hw,-hh],[hw,hh],[-hw,hh]].map(([dx,dy])=>{
    const e=dx*Math.cos(a)-dy*Math.sin(a), n=dx*Math.sin(a)+dy*Math.cos(a);
    return [lat + n/111320, lon + e/(111320*coslat)];
  });
}
function drawFrame(){
  frameLayer.clearLayers();
  if(!frame){$('#frameInfo').textContent='Sem folha. Centralize o mapa e clique "Definir folha".';$('#bFrame').textContent='Definir folha'; if(ringsOn) drawRings(); return;}
  const {w,h}=a3dims(); const corners=rectCorners(frame.lat,frame.lon,w,h,frame.angle);
  L.polygon(corners,{color:'#2f6df0',weight:2,fill:true,fillOpacity:.04,dashArray:'6,4'}).addTo(frameLayer);
  const tip=rectCorners(frame.lat,frame.lon,0,h*0.9,frame.angle)[3];
  L.polyline([[frame.lat,frame.lon],tip],{color:'#2f6df0',weight:1}).addTo(frameLayer);
  const c=L.marker([frame.lat,frame.lon],{draggable:true,title:'arraste a folha'}).addTo(frameLayer);
  c.on('drag',ev=>{frame.lat=ev.latlng.lat;frame.lon=ev.latlng.lng;});
  c.on('dragend',()=>{drawFrame();markDirty();});
  $('#bFrame').textContent='Remover folha';
  $('#frameInfo').innerHTML=`A3 ${esc($('#pScale').value)} — <b>${(w/1000).toFixed(2)} × ${(h/1000).toFixed(2)} km</b> · ${frame.angle}°`;
  if(ringsOn) drawRings();
}
function toggleFrame(){
  if(frame){frame=null;drawFrame();markDirty();return;}
  const c=map.getCenter(); frame={lat:c.lat,lon:c.lng,angle:+$('#fAngle').value};
  drawFrame(); markDirty();
}

function setMode(m){mode=m; tmpVerts=[]; tmpLayer.clearLayers();
  [['mPoint','point'],['mProib','proib'],['mAten','aten'],['mRoute','route'],['mLand','pouso']]
    .forEach(([id,v])=>{const el=$('#'+id); if(el) el.classList.toggle('active',m===v);});
  $('#mode').textContent = ({point:'Ponto',proib:'Área proibida',aten:'Área atenção',route:'Rota/Corredor',pouso:'Pouso'})[m]||m;
  $('#modeHelp').textContent = ({point:'Clique no mapa para adicionar o ponto selecionado.',
    proib:'Clique p/ vértices; duplo-clique encerra a área.', aten:'Clique p/ vértices; duplo-clique encerra a área.',
    route:'Clique p/ vértices da rota; duplo-clique encerra.', pouso:'Clique no mapa para marcar um pouso.'})[m]||'';
  if(m==='point') map.doubleClickZoom.enable(); else map.doubleClickZoom.disable();
}

function nextName(type){
  if(type==='SP') return 'SP';
  if(type==='FP') return 'FP';
  if(type==='TP') return String(points.filter(p=>p.type==='TP').length+1);
  if(type==='HG') return 'FXC'+String(points.filter(p=>p.type==='HG').length+1).padStart(3,'0');
  if(type==='TG') return 'TG'+String(points.filter(p=>p.type==='TG').length+1);
  return type;
}
function onClick(e){
  if(suppressClick){ suppressClick=false; return; }
  const ll=[e.latlng.lat, e.latlng.lng];
  if(mode==='point'){
    const type=$('#pNext').value;
    if((type==='SP'||type==='FP') && points.some(p=>p.type===type)){
      alert('Já existe um '+type+'. Edite o existente na tabela ou troque o "próximo ponto".'); return; }
    points.push({id:uid(),name:nextName(type),type,radius:R(type),weight:1,lat:ll[0],lon:ll[1]});
    if(type==='SP'){ const sel=$('#pNext'); if([...sel.options].some(o=>o.value==='TP')) sel.value='TP'; }
    markDirty(); render();
  } else if(mode==='route'){
    if(!route) route={coords:[],width:+$('#rWidth').value||300};
    route.coords.push(ll); markDirty(); renderRoute();
  } else if(mode==='pouso'){
    landings.push({id:uid(),name:'Pouso '+(landings.length+1),lat:ll[0],lon:ll[1]}); markDirty(); render();
  } else {
    tmpVerts.push(ll); drawTmp();
  }
}

/* rota/corredor (N3) */
function renderRoute(){
  routeLayer.clearLayers();
  if(!route || route.coords.length<1) return;
  if(route.coords.length>1){
    const poly=corridorPolygon(route.coords, route.width/2);
    if(poly) L.polygon(poly,{color:'#0ea5e9',weight:1,fillColor:'#0ea5e9',fillOpacity:.15})
      .bindTooltip(`Corredor ${route.width} m`).addTo(routeLayer);
    L.polyline(route.coords,{color:'#0ea5e9',weight:2,dashArray:'6 4'}).addTo(routeLayer);
  }
  route.coords.forEach((c,i)=>{
    const m=L.marker(c,{draggable:true,icon:vertexIcon('#0ea5e9')}).addTo(routeLayer);
    m.bindTooltip(String(i+1),{permanent:true,direction:'center',className:'wp-lbl'});
    m.on('drag',ev=>{route.coords[i]=[ev.latlng.lat,ev.latlng.lng];});
    m.on('dragend',()=>{markDirty();renderRoute();});
    m.on('contextmenu',ev=>{L.DomEvent.stopPropagation(ev); if(route.coords.length>2){route.coords.splice(i,1);markDirty();renderRoute();}});
  });
}
function drawTmp(){tmpLayer.clearLayers();
  const col = mode==='proib'?'#e53935':'#f9a825';
  if(tmpVerts.length) L.polyline(tmpVerts,{color:col,dashArray:'4,4'}).addTo(tmpLayer);
  tmpVerts.forEach(v=>L.circleMarker(v,{radius:3,color:col,fillOpacity:1}).addTo(tmpLayer));
}
function finishArea(){
  if(tmpVerts.length>=3){ areas.push({kind: mode==='proib'?'proibida':'atencao', name:'', coords:tmpVerts.slice()}); markDirty(); }
  tmpVerts=[]; tmpLayer.clearLayers(); render();
}

function render(){
  ptLayer.clearLayers(); areaLayer.clearLayers(); landLayer.clearLayers();
  areas.forEach((a,ai)=>{const col=a.kind==='proibida'?'#e53935':'#f9a825';
    a._p=L.polygon(a.coords,{color:col,fillColor:col,fillOpacity:.25,weight:2}).addTo(areaLayer);
    a._p.on('click',ev=>{suppressClick=true; L.DomEvent.stopPropagation(ev);
      if(confirm('Remover esta área?')){areas.splice(ai,1);markDirty();render();}});
    a.coords.forEach((c,vi)=>{
      const vm=L.marker(c,{draggable:true,icon:vertexIcon(col)}).addTo(areaLayer);
      vm.on('drag',ev=>{a.coords[vi]=[ev.latlng.lat,ev.latlng.lng]; a._p.setLatLngs(a.coords);});
      vm.on('dragend',()=>{markDirty();render();});
      vm.on('contextmenu',ev=>{L.DomEvent.stopPropagation(ev);
        if(a.coords.length>3){a.coords.splice(vi,1);markDirty();render();} else alert('Área precisa de ≥3 vértices.');});
    });
  });
  landings.forEach((p,i)=>{
    const m=L.marker([p.lat,p.lon],{draggable:true}).addTo(landLayer);
    m.bindTooltip('🛬 '+p.name,{permanent:true,direction:'top',className:'wp-lbl',offset:[0,-4]});
    m.on('drag',ev=>{p.lat=ev.latlng.lat;p.lon=ev.latlng.lng;});
    m.on('dragend',()=>{markDirty();render();});
    m.on('contextmenu',ev=>{L.DomEvent.stopPropagation(ev); if(confirm('Remover pouso "'+p.name+'"?')){landings.splice(i,1);markDirty();render();}});
  });
  points.forEach((p)=>{const col=TYPECOL[p.type]||'#888';
    L.circle([p.lat,p.lon],{radius:+p.radius,color:col,fillOpacity:.05,weight:1}).addTo(ptLayer);
    const m=L.marker([p.lat,p.lon],{draggable:true}).addTo(ptLayer);
    m.bindTooltip(`${p.name} (${p.type})`,{permanent:true,direction:'top',className:'wp-lbl',offset:[0,-4]});
    m.on('drag', ev=>{p.lat=ev.latlng.lat;p.lon=ev.latlng.lng;});
    m.on('dragend', ()=>{markDirty();render();});
    p._m=m;
  });
  if(ringsOn) drawRings();
  renderTable();
  markDirty();
}
function renderTable(){
  const tb=$('#ptTable tbody'); if(!tb) return; tb.innerHTML='';
  const allowed = POINT_TYPES_BY[provaType()] || ['SP','TP','HG','TG','FP'];
  points.forEach((p,i)=>{
    const tr=document.createElement('tr');
    const tdN=document.createElement('td'); tdN.textContent=i+1;
    const tdName=document.createElement('td');
    const inName=document.createElement('input'); inName.className='form-control form-control-sm'; inName.style.width='64px'; inName.value=p.name;
    inName.onchange=()=>{p.name=inName.value;markDirty();render();}; tdName.appendChild(inName);
    const tdType=document.createElement('td');
    const sel=document.createElement('select'); sel.className='form-select form-select-sm';
    const types = allowed.includes(p.type) ? allowed : allowed.concat([p.type]);
    types.forEach(t=>{const o=document.createElement('option');o.value=t;o.textContent=t;if(t===p.type)o.selected=true;sel.appendChild(o);});
    sel.onchange=()=>{p.type=sel.value;p.radius=R(p.type);markDirty();render();}; tdType.appendChild(sel);
    const tdR=document.createElement('td');
    const inRad=document.createElement('input'); inRad.type='number'; inRad.className='form-control form-control-sm'; inRad.style.width='64px'; inRad.value=p.radius;
    inRad.onchange=()=>{p.radius=+inRad.value;markDirty();render();}; tdR.appendChild(inRad);
    const tdD=document.createElement('td');
    const btn=document.createElement('button'); btn.className='btn btn-sm btn-outline-danger py-0'; btn.textContent='×';
    btn.onclick=()=>{points.splice(i,1);markDirty();render();}; tdD.appendChild(btn);
    tr.append(tdN,tdName,tdType,tdR,tdD); tb.appendChild(tr);
  });
}

function renumberTPs(){ let n=0; points.forEach(p=>{ if(p.type==='TP'){ n++; p.name=String(n); } }); markDirty(); render(); }

function genGates(){
  const main = points.filter(p=>p.type!=='HG');
  if(main.length<2){alert('Defina ao menos SP e FP (e turnpoints) primeiro.');return;}
  const sp = +(prompt('Espaçamento dos hidden gates (m):','1000')||0);
  if(!sp){return;}
  const out=[]; let hgN=0;
  for(let i=0;i<main.length;i++){
    out.push(main[i]);
    if(i<main.length-1){
      const a=[main[i].lat,main[i].lon], b=[main[i+1].lat,main[i+1].lon];
      const d=haversine(a,b); const n=Math.max(0,Math.round(d/sp)-1);
      for(let k=1;k<=n;k++){const f=k/(n+1);hgN++;
        out.push({id:uid(),name:'FXC'+String(hgN).padStart(3,'0'),type:'HG',radius:R('HG'),weight:1,
          lat:a[0]+(b[0]-a[0])*f, lon:a[1]+(b[1]-a[1])*f});}
    }
  }
  points=out; markDirty(); render();
}

let ringsOn=false;
/* maior raio (m) de um círculo centrado em `c` que ainda cabe DENTRO do
   retângulo da folha A3 (`fr`), respeitando a rotação. = distância à borda mais próxima. */
function inscribedRadius(c, fr){
  const {w,h}=a3dims(); const hw=w/2, hh=h/2;
  const a=(fr.angle||0)*Math.PI/180, coslat=Math.cos(fr.lat*Math.PI/180);
  const e=(c[1]-fr.lon)*111320*coslat, n=(c[0]-fr.lat)*111320;   // centro→folha (m)
  const dx=e*Math.cos(a)+n*Math.sin(a), dy=-e*Math.sin(a)+n*Math.cos(a);  // coords locais do retângulo
  return Math.min(hw-Math.abs(dx), hh-Math.abs(dy));
}
/* anéis de peso (N1): 2 anéis que dividem a prova em 3 faixas iguais até a borda
   da folha A3 (centro = ponto médio SP–FP). Peso cresce com a distância (1/2/3). */
function ringCenter(){
  const sp=points.find(p=>p.type==='SP'), fp=points.find(p=>p.type==='FP');
  return (sp&&fp) ? [(sp.lat+fp.lat)/2,(sp.lon+fp.lon)/2] : null;
}
function drawRings(){
  ringLayer.clearLayers();
  if(!ringsOn) return;
  const c=ringCenter(); if(!c || !frame) return;
  const Rmax=inscribedRadius(c, frame); if(Rmax<=0) return;
  const r1=Rmax/3, r2=2*Rmax/3;
  [r1,r2].forEach(r=>L.circle(c,{radius:r,color:'#fff',weight:1,dashArray:'5,6',fillOpacity:0}).addTo(ringLayer));
  L.circleMarker(c,{radius:3,color:'#fff',fillOpacity:1}).bindTooltip(
    `Anéis: ${(r1/1000).toFixed(1)} / ${(r2/1000).toFixed(1)} km (peso 1·2·3)`).addTo(ringLayer);
  points.forEach(p=>{ if(p.type==='TP'){const d=haversine(c,[p.lat,p.lon]); p.weight = d<=r1?1:(d<=r2?2:3);} });
}
function toggleRings(){
  if(ringsOn){ ringsOn=false; ringLayer.clearLayers(); render(); return; }
  if(!ringCenter()){alert('Defina SP e FP para traçar os anéis.');return;}
  if(!frame){alert('Defina a folha A3 (o retângulo da prova) primeiro — os anéis se ajustam a ela.');return;}
  if(inscribedRadius(ringCenter(), frame)<=0){alert('O ponto médio SP–FP está fora da folha. Reposicione a folha.');return;}
  ringsOn=true; drawRings(); markDirty(); render();
}

function provaObj(){
  const slug=(window.PROVA_INIT && window.PROVA_INIT.prova) ? (window.PROVA_INIT.prova.slug||'') : '';
  const ms=mapMode();
  const o={prova:{name:$('#pName').value, type:provaType(), slug, mapSlug:ms||'',
      scale:$('#pScale').value, teto:+$('#pTeto').value, alturaMin:+$('#pAlt').value, windowMin:+$('#pWin').value}};
  // Com mapa, a geometria vem do mapa (não enviar inline).
  if(ms){ o.points=[]; o.areas=[]; o.frame={}; o.route={}; o.landings=[]; return o; }
  o.points=points.map(p=>({name:p.name,type:p.type,radius:+p.radius,weight:+p.weight,lat:p.lat,lon:p.lon,alt:0}));
  o.areas=areas.map(a=>({kind:a.kind,name:a.name||'',coords:a.coords}));
  o.frame=frame||{};
  o.route=(route && route.coords.length>1) ? {coords:route.coords, width:+route.width} : {};
  o.landings=landings.map(p=>({name:p.name,lat:p.lat,lon:p.lon}));
  return o;
}
function validate(){
  // Com mapa, a geometria/validação fica no mapa (servidor confere SP/FP/rota do mapa).
  if(mapMode()) return [];
  const t=provaType(); const errs=[];
  if(!points.some(p=>p.type==='SP')) errs.push('Falta o ponto SP (largada).');
  if(!points.some(p=>p.type==='FP')) errs.push('Falta o ponto FP (chegada).');
  points.forEach(p=>{ if(!(+p.radius>0)) errs.push('Raio inválido no ponto "'+p.name+'".');
    if(!isFinite(p.lat)||!isFinite(p.lon)) errs.push('Coordenada inválida no ponto "'+p.name+'".'); });
  if(t==='n3' && !(route && route.coords.length>=2)) errs.push('N3 precisa de uma rota com ≥2 vértices.');
  if(t==='n1' && points.some(p=>p.type==='HG'||p.type==='TG')) errs.push('N1 não usa HG/TG — remova-os ou troque o tipo.');
  if(t!=='n3' && route && route.coords.length) errs.push('Há uma rota desenhada, mas o tipo não é N3.');
  return [...new Set(errs)];
}
function save(asNew){
  const errs=validate();
  if(errs.length){ $('#saveMsg').innerHTML='<span class="text-danger">⚠ '+errs.map(esc).join('<br>')+'</span>'; return; }
  const obj=provaObj();
  if(asNew){ obj.prova.slug=''; obj.prova.saveAs=true; }
  $('#saveMsg').textContent='Salvando…';
  fetch('/builder/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(obj)})
    .then(r=>r.json()).then(d=>{
      if(!d.ok){ $('#saveMsg').innerHTML='<span class="text-danger">'+esc(d.error||'Erro ao salvar.')+'</span>'; return; }
      clearDraft();
      window.PROVA_INIT = window.PROVA_INIT || {prova:{}}; window.PROVA_INIT.prova = window.PROVA_INIT.prova || {};
      window.PROVA_INIT.prova.slug = d.slug;
      $('#saveMsg').innerHTML='<span class="text-success">Salva como <b>'+esc(d.slug)+'</b>.</span> · '
        +'<a href="/scores?sala='+encodeURIComponent(d.slug)+'">Scores</a> · '
        +'<a href="/prova/'+encodeURIComponent(d.slug)+'/mapa.pdf">Mapa A3</a>';
    })
    .catch(()=>$('#saveMsg').innerHTML='<span class="text-danger">Erro ao salvar.</span>');
}
function dl(name,txt,mime){const b=new Blob([txt],{type:mime});const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download=name;a.click();}
function exportJSON(){dl(($('#pName').value||'prova')+'.json', JSON.stringify(provaObj(),null,2),'application/json');}
function exportKML(){
  const pm = points.map(p=>`<Placemark><name>${xmlEsc(p.name)}</name><description>${xmlEsc(p.type+' r='+p.radius+'m')}</description><Point><coordinates>${p.lon},${p.lat},0</coordinates></Point></Placemark>`).join('');
  const ar = areas.map(a=>`<Placemark><name>${xmlEsc(a.kind)}</name><Polygon><outerBoundaryIs><LinearRing><coordinates>${a.coords.concat([a.coords[0]]).map(c=>c[1]+','+c[0]+',0').join(' ')}</coordinates></LinearRing></outerBoundaryIs></Polygon></Placemark>`).join('');
  const rt = (route && route.coords.length>1) ? `<Placemark><name>${xmlEsc('Rota (corredor '+route.width+' m)')}</name><LineString><coordinates>${route.coords.map(c=>c[1]+','+c[0]+',0').join(' ')}</coordinates></LineString></Placemark>` : '';
  const ld = landings.map(p=>`<Placemark><name>${xmlEsc(p.name)}</name><Point><coordinates>${p.lon},${p.lat},0</coordinates></Point></Placemark>`).join('');
  dl(($('#pName').value||'prova')+'.kml',
    `<?xml version="1.0" encoding="UTF-8"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>${xmlEsc($('#pName').value)}</name>${pm}${ar}${rt}${ld}</Document></kml>`,
    'application/vnd.google-earth.kml+xml');
}

function loadInit(d){
  loading=true;
  d=d||{prova:{}}; const pr=d.prova||{};
  $('#pName').value=pr.name||'Nova prova'; $('#pType').value=pr.type||'n1';
  if($('#pMap') && (pr.mapSlug||pr.map_slug)){ const opt=[...$('#pMap').options].some(o=>o.value===(pr.mapSlug||pr.map_slug)); if(opt) $('#pMap').value=(pr.mapSlug||pr.map_slug); }
  if(pr.scale)$('#pScale').value=pr.scale;
  $('#pTeto').value=pr.teto||0; $('#pAlt').value=pr.alturaMin||pr.altura_min||0; $('#pWin').value=pr.windowMin||pr.window_min||60;
  points=(d.points||[]).map(p=>({id:uid(),name:p.name,type:p.type,radius:p.radius,weight:p.weight||1,lat:p.lat,lon:p.lon}));
  areas=(d.areas||[]).map(a=>({kind:a.kind,name:a.name||'',coords:a.coords}));
  frame=(d.frame && d.frame.lat) ? {lat:d.frame.lat,lon:d.frame.lon,angle:d.frame.angle||0} : null;
  if(frame){$('#fAngle').value=frame.angle;$('#angLbl').textContent=frame.angle;}
  route=(d.route && d.route.coords && d.route.coords.length) ? {coords:d.route.coords.map(c=>[c[0],c[1]]),width:d.route.width||300} : null;
  if(route)$('#rWidth').value=route.width;
  landings=(d.landings||[]).map(p=>({id:uid(),name:p.name||'Pouso',lat:p.lat,lon:p.lon}));
  render(); drawFrame(); renderRoute(); applyTypeUI();
  if(points.length){try{map.fitBounds(L.latLngBounds(points.map(p=>[p.lat,p.lon])).pad(0.2));}catch(e){}}
  loading=false;
}

document.addEventListener('DOMContentLoaded', init);
