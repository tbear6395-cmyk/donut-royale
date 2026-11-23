import * as T from "https://unpkg.com/three@0.160.1/build/three.module.min.js";

export function createBoard(canvas, select){
  const renderer=new T.WebGLRenderer({canvas,antialias:true,alpha:true,powerPreference:"low-power"});
  renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.shadowMap.enabled=true;
  renderer.shadowMap.type=T.PCFSoftShadowMap;
  const scene=new T.Scene(), camera=new T.OrthographicCamera(-5,5,5,-5,.1,80);
  camera.position.set(0,12,8);camera.lookAt(0,0,0);
  scene.add(new T.HemisphereLight(0xfff2d6,0x728387,2.1));
  const lamp=new T.DirectionalLight(0xffe0b2,3.1);
  lamp.position.set(-4,9,4);lamp.castShadow=true;lamp.shadow.mapSize.set(1024,1024);
  Object.assign(lamp.shadow.camera,{left:-7,right:7,top:7,bottom:-7});lamp.shadow.normalBias=.012;scene.add(lamp);
  const rim=new T.DirectionalLight(0xa6d9ff,1.7);rim.position.set(5,5,-5);scene.add(rim);
  const mat=(color,metalness=.13)=>new T.MeshStandardMaterial({color,metalness,roughness:.37});
  const ivory=mat(0xffecc5), obsidian=mat(0x26394c), gold=mat(0xd8ae61,.65), walnut=mat(0x533526);
  const tiles=[mat(0xf0dcb0),mat(0x527975)],focus=mat(0xe8ad50),legal=mat(0x94ac5c);
  const lightBand=mat(0xb48a47,.5),darkBand=mat(0x7699ac,.6);
  const mesh=(geometry,material,group,x,y,z)=>{
    const m=new T.Mesh(geometry,material);m.position.set(x,y,z);m.castShadow=true;m.receiveShadow=true;group.add(m);return m;
  };
  mesh(new T.BoxGeometry(8.5,.36,8.5),walnut,scene,0,-.23,0);
  mesh(new T.BoxGeometry(8.36,.075,8.36),gold,scene,0,-.075,0);
  const squareGeo=new T.BoxGeometry(.994,.085,.994), board=[];
  for(let r=0;r<8;r++)for(let f=0;f<8;f++){
    const tile=mesh(squareGeo,tiles[(r+f)%2],scene,f-3.5,0,r-3.5);
    tile.userData.square="abcdefgh"[f]+(8-r);board.push(tile);
  }
  // Put square coordinates on the frame, outside the hit targets.
  function label(text,x,z){
    const tag=document.createElement("canvas");tag.width=64;tag.height=64;
    const ctx=tag.getContext("2d");ctx.fillStyle="#f6e8ba";ctx.font="bold 46px Georgia";ctx.textAlign="center";ctx.textBaseline="middle";ctx.fillText(text,32,32);
    const tex=new T.CanvasTexture(tag);tex.colorSpace=T.SRGBColorSpace;
    const plate=new T.Mesh(new T.PlaneGeometry(.21,.21), new T.MeshBasicMaterial({map:tex,transparent:true,depthWrite:false}));
    plate.rotation.x=-Math.PI/2;plate.position.set(x,-.035,z);scene.add(plate);
  }
  for(let i=0;i<8;i++){label("abcdefgh"[i],i-3.5,4.11);label(String(8-i),-4.11,i-3.5);}
  const lathe=points=>new T.LatheGeometry(points.map(([x,y])=>new T.Vector2(x,y)),32);
  const body=lathe([[0,0],[.32,0],[.34,.05],[.32,.1],[.26,.13],[.29,.16],[.27,.20],[.19,.24],[.135,.35],[.115,.46],[.17,.51],[.18,.55],[0,.55]]);
  const collar=new T.CylinderGeometry(.25,.26,.045,32),orb=new T.SphereGeometry(1,20,16);
  const cylinder=new T.CylinderGeometry(1,1,1,24),cube=new T.BoxGeometry(1,1,1);
  const horse=new T.Shape();horse.moveTo(-.22,0);for(const [x,y] of [[-.18,.23],[-.07,.5],[-.05,.63],[.04,.59],[.09,.7],[.13,.54],[.30,.36],[.27,.27],[.15,.26],[.04,.32],[.01,.19],[.16,0]])horse.lineTo(x,y);
  horse.closePath();
  const horseGeo=new T.ExtrudeGeometry(horse,{depth:.17,bevelEnabled:true,bevelThickness:.035,bevelSize:.035,bevelSegments:2,steps:1});horseGeo.center();
  const templates={};
  for(const color of ["w","b"])for(const type of "pnbrqk"){
    const g=new T.Group(),m=color==="w"?ivory:obsidian,band=color==="w"?lightBand:darkBand;
    mesh(body,m,g,0,0,0);mesh(collar,band,g,0,.14,0);
    const part=(shape,material,x,y,z,sx,sy,sz)=>{const o=mesh(shape,material,g,x,y,z);o.scale.set(sx,sy,sz);return o;};
    if(type==="p")part(orb,m,0,.64,0,.205,.205,.205);
    if(type==="n"){const n=mesh(horseGeo,m,g,0,.78,0);n.rotation.y=color==="w"?-.35:2.8;}
    if(type==="b"){part(orb,m,0,.72,0,.195,.30,.195);part(orb,band,0,1.03,0,.055,.055,.055);const slash=part(cube,band,.052,.80,.16,.033,.17,.022);slash.rotation.z=-.42;}
    if(type==="r"){part(cylinder,m,0,.65,0,.235,.23,.235);for(let i=0;i<6;i++){const a=i*Math.PI/3;part(cube,m,.19*Math.cos(a),.82,.19*Math.sin(a),.105,.15,.11).rotation.y=-a;}}
    if(type==="q"||type==="k"){
      part(cylinder,m,0,.68,0,.17,.28,.17);part(collar,band,0,.81,0,.93,1,.93);
      if(type==="q"){for(let i=0;i<7;i++){const a=i*Math.PI*2/7;part(orb,m,.15*Math.cos(a),.91,.15*Math.sin(a),.062,.125,.062);}part(orb,band,0,1.02,0,.075,.085,.075);}
      else{part(orb,m,0,.91,0,.17,.14,.17);part(cube,band,0,1.13,0,.075,.27,.075);part(cube,band,0,1.15,0,.22,.065,.07);}
    }
    templates[color+type]=g;
  }
  let pieces=new T.Group();scene.add(pieces);
  const pointer=new T.Vector2(),ray=new T.Raycaster();
  canvas.addEventListener("click",e=>{
    const rect=canvas.getBoundingClientRect();pointer.set((e.clientX-rect.left)/rect.width*2-1,1-(e.clientY-rect.top)/rect.height*2);
    ray.setFromCamera(pointer,camera);
    const hit=ray.intersectObjects([...pieces.children,...board],true)[0];let obj=hit?.object;
    while(obj&&!obj.userData.square)obj=obj.parent;
    if(obj)select(obj.userData.square);
  });
  const paint=()=>{const width=canvas.clientWidth,height=canvas.clientHeight;if(!width||!height)return;
    const ratio=width/height;camera.right=Math.max(4.65,4.2*ratio);camera.left=-camera.right;camera.top=camera.right/ratio;camera.bottom=-camera.top;
    camera.updateProjectionMatrix();renderer.setSize(width,height,false);renderer.render(scene,camera);};
  new ResizeObserver(paint).observe(canvas);
  return (position,selected,moves)=>{
    pieces.clear();position.flat().forEach(p=>{if(!p)return;const g=templates[p.color+p.type].clone();
      g.userData.square=p.square;g.position.set(p.square.charCodeAt(0)-97-3.5,.045,8-Number(p.square[1])-3.5);pieces.add(g);});
    board.forEach((tile,i)=>{const sq=tile.userData.square;tile.material=sq===selected?focus:moves.some(m=>m.to===sq)?legal:tiles[(Math.floor(i/8)+i%8)%2];});
    paint();
  };
}
