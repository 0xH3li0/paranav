/* Viewer: prova + trajetos de todos os pilotos da Sala. */
const TYPECOL = {SP:'#19c37d', FP:'#ff5d9e', TP:'#3fa7ff', HG:'#c4a8ff', TG:'#ffd08f'};
const PAL=['#3fa7ff','#19c37d','#ffb020','#ff5d5d','#c4a8ff','#ff8fc6','#8fffc6','#ffd08f'];

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
    const nx=-dy, ny=dx;
    left.push([xy[i][0]+nx*halfM, xy[i][1]+ny*halfM]);
    right.push([xy[i][0]-nx*halfM, xy[i][1]-ny*halfM]);
  }
  return left.concat(right.reverse()).map(q=>[lat0+q[1]/mLat, lon0+q[0]/mLon]);
}

document.addEventListener('DOMContentLoaded', async ()=>{
  const el=document.getElementById('map');
  const slug=el.dataset.slug;
  const map=L.map('map').setView([-22.88,-42.6],12);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:18,attribution:'© OpenStreetMap'}).addTo(map);
  const all=[];
  if(slug){
    const d=await fetch(`/api/sala/${encodeURIComponent(slug)}/mapdata`).then(r=>r.json());
    if(d.route && d.route.coords && d.route.coords.length>1){
      const poly=corridorPolygon(d.route.coords, (d.route.width||0)/2);
      if(poly){const corr=L.polygon(poly,{color:'#ffae42',weight:1,fillColor:'#ffae42',fillOpacity:.12})
        .bindTooltip(`Corredor (largura ${d.route.width} m)`).addTo(map);all.push(corr);}
      const cl=L.polyline(d.route.coords,{color:'#ffae42',weight:2,dashArray:'6 4',opacity:.9}).addTo(map);all.push(cl);
    }
    (d.landings||[]).forEach(p=>{const m=L.marker([p.lat,p.lon]).bindTooltip(`🛬 ${p.name}`).addTo(map);all.push(m);});
    (d.wpts||[]).forEach(w=>{const col=TYPECOL[w.type]||'#888';
      const c=L.circle([w.lat,w.lon],{radius:w.radius,color:col,weight:1,fillOpacity:.05}).addTo(map);all.push(c);
      const m=L.circleMarker([w.lat,w.lon],{radius:4,color:'#fff',fillColor:col,fillOpacity:1,weight:1}).bindTooltip(`${w.name} (${w.type})`).addTo(map);all.push(m);});
    const t=await fetch(`/api/sala/${encodeURIComponent(slug)}/trackdata`).then(r=>r.json());
    let leg=[];
    (t.tracks||[]).forEach((tr,i)=>{const col=PAL[i%PAL.length];
      const line=L.polyline(tr.fixes,{color:col,weight:2.5,opacity:.85}).bindTooltip(`${tr.bib} · ${tr.name}`).addTo(map);all.push(line);
      leg.push(`<span style="color:${col}">━</span> ${tr.name}`);});
    document.getElementById('legend').innerHTML=leg.join(' &nbsp; ');
  }
  if(all.length){try{map.fitBounds(L.featureGroup(all).getBounds().pad(0.12));}catch(e){}}
});
