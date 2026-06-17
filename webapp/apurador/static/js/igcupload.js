/* Pré-visualização da prova + trajeto do IGC antes de enviar. */
const TYPECOL = {SP:'#19c37d', FP:'#ff5d9e', TP:'#3fa7ff', HG:'#c4a8ff', TG:'#ffd08f'};
let map, wptLayer, trackLayer;

function ensureMap(){
  if(map) return;
  map = L.map('map').setView([-22.88,-42.6],12);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:18,attribution:'© OpenStreetMap'}).addTo(map);
  wptLayer = L.layerGroup().addTo(map);
  trackLayer = L.layerGroup().addTo(map);
}
function drawWPTs(wpts){
  wptLayer.clearLayers();
  const types={};
  wpts.forEach(w=>{
    const col=TYPECOL[w.type]||'#888';
    L.circle([w.lat,w.lon],{radius:w.radius,color:col,weight:1,fillOpacity:.05}).addTo(wptLayer);
    L.circleMarker([w.lat,w.lon],{radius:4,color:'#fff',fillColor:col,fillOpacity:1,weight:1})
      .bindTooltip(`${w.name} (${w.type})`).addTo(wptLayer);
    types[w.type]=(types[w.type]||0)+1;
  });
  if(wpts.length){const g=L.featureGroup(wptLayer.getLayers());try{map.fitBounds(g.getBounds().pad(0.12));}catch(e){}}
  document.getElementById('legend').innerHTML=Object.entries(types).map(([t,n])=>`<b style="color:${TYPECOL[t]}">${t}</b>: ${n}`).join(' · ');
}
async function loadSala(slug){
  ensureMap();
  if(!slug){wptLayer.clearLayers();return;}
  const d=await fetch(`/api/sala/${encodeURIComponent(slug)}/mapdata`).then(r=>r.json());
  if(d.has_prova) drawWPTs(d.wpts);
}
/* parser IGC mínimo só p/ preview do trajeto */
function igcToDec(line){
  const laD=+line.substr(7,2),laM=+line.substr(9,5)/1000,laH=line[14];
  const loD=+line.substr(15,3),loM=+line.substr(18,5)/1000,loH=line[23];
  let lat=laD+laM/60; if(laH==='S')lat=-lat;
  let lon=loD+loM/60; if(loH==='W')lon=-lon;
  return [lat,lon];
}
function parseIGC(text){
  const pts=[];
  for(const raw of text.split(/\r?\n/)){const l=raw.trim();
    if(l[0]==='B'&&l.length>=35){const[la,lo]=igcToDec(l);if(!isNaN(la)&&!isNaN(lo))pts.push([la,lo]);}}
  return pts;
}
function drawTrackPreview(points){
  trackLayer.clearLayers();
  if(!points||points.length<2)return;
  const line=L.polyline(points,{color:'#3fa7ff',weight:2.5,opacity:.85}).addTo(trackLayer);
  try{map.fitBounds(line.getBounds().pad(0.12));}catch(e){}
}

document.addEventListener('DOMContentLoaded',()=>{
  ensureMap();
  const sel=document.getElementById('sala');
  sel.addEventListener('change',()=>loadSala(sel.value));
  const fi=document.getElementById('igcfile');
  fi.addEventListener('change',ev=>{const f=ev.target.files[0];if(!f)return;
    const rd=new FileReader();rd.onload=()=>drawTrackPreview(parseIGC(rd.result));rd.readAsText(f);});
});
