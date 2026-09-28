/* ================= the ballad (Web Audio) ================= */
const AUD={playing:false,bpm:60};
(function(){
  let AC,sfxBus,sfxRev,sfxUntil=0,master,bandBus,bandPan,bandDist,revIn,ch={},SAMP={},crowdBus,timer=null,t0=0,beat=0,loaded=false,loading=null;
  const evq=[];const SPB=60/AUD.bpm, SW=.6;
  // D minor ballad, 16 bars; each bar: list of [rootPc, quality, beats]
  const FORM=[
    [[2,"m9",4]],[[10,"maj7",4]],[[7,"m9",4]],[[9,"7b9",4]],
    [[2,"m9",4]],[[0,"9",4]],[[5,"maj9",4]],[[4,"m7b5",2],[9,"7b9",2]],
    [[10,"maj7",4]],[[9,"m7",4]],[[7,"m9",4]],[[0,"9",4]],
    [[5,"maj9",4]],[[10,"maj7",4]],[[4,"m7b5",2],[9,"7b9",2]],[[2,"m9",2],[9,"7b9",2]]
  ];
  const TONES={m9:[0,3,7,10,14],maj7:[0,4,7,11,14],"7b9":[0,4,7,10,13],"9":[0,4,7,10,14],maj9:[0,4,7,11,14],m7b5:[0,3,6,10],m7:[0,3,7,10,14]};
  const SCALE={m9:[0,2,3,5,7,9,10],maj7:[0,2,4,6,7,9,11],"7b9":[0,1,4,5,7,8,10],"9":[0,2,4,5,7,9,10],maj9:[0,2,4,5,7,9,11],m7b5:[0,1,3,5,6,8,10],m7:[0,2,3,5,7,8,10]};
  const UPPER={m9:[[3,7,10,14],[10,14,15,19]],maj7:[[4,7,11,14],[11,14,16,19]],"7b9":[[4,8,10,13],[10,13,16,20]],"9":[[4,9,10,14],[10,14,16,21]],maj9:[[4,7,11,14],[11,14,16,19]],m7b5:[[3,6,10,12],[10,12,15,18]],m7:[[3,7,10,14],[10,14,15,19]]};
  const pc=m=>((m%12)+12)%12;
  function chordAt(bar,b){const segs=FORM[bar%FORM.length];let acc=0;for(const s of segs){if(b<acc+s[2])return {root:s[0],q:s[1],start:acc,len:s[2]};acc+=s[2];}return {root:segs[0][0],q:segs[0][1],start:0,len:4};}
  function b64(s){const bin=atob(s),u=new Uint8Array(bin.length);for(let i=0;i<bin.length;i++)u[i]=bin.charCodeAt(i);return u.buffer;}
  function sat(k){const n=2048,c=new Float32Array(n);for(let i=0;i<n;i++){const x=i/(n-1)*2-1;c[i]=Math.tanh(k*x)/Math.tanh(k);}return c;}
  function ir(dur){const sr=AC.sampleRate,len=Math.floor(sr*dur),b=AC.createBuffer(2,len,sr);
    for(let c=0;c<2;c++){const d=b.getChannelData(c);let lp=0;
      [[.013,.5],[.021,.38],[.029,.3],[.041,.26],[.053,.2],[.067,.16]].forEach(([t,a])=>{d[Math.floor((t+(c?.003:0))*sr)]+=a*(Math.random()<.5?-1:1);});
      const pre=Math.floor(.02*sr);for(let i=pre;i<len;i++){const t=(i-pre)/sr, env=Math.exp(-6.9*t/(dur-.02)), a=.85*Math.exp(-t*1.6)+.08; lp+=a*((Math.random()*2-1)-lp); d[i]+=lp*env*.55;}}
    return b;}
  function mkCh(pan,send,{lp=18000,gain=1}={}){const g=AC.createGain();g.gain.value=gain;const f=AC.createBiquadFilter();f.type="lowpass";f.frequency.value=lp;const p=AC.createStereoPanner();p.pan.value=pan;const s=AC.createGain();s.gain.value=send;g.connect(f);f.connect(p);p.connect(bandBus);f.connect(s);s.connect(revIn);return g;}
  function ensureCtx(){
    if(AC)return;
    AC=new (window.AudioContext||window.webkitAudioContext)({latencyHint:"playback"});
    const nb=AC.createBuffer(1,AC.sampleRate*2,AC.sampleRate);const nd=nb.getChannelData(0);for(let i=0;i<nd.length;i++)nd[i]=Math.random()*2-1;SAMP.noise=nb;
    // sound-effects path: its own gentle bus straight to the output, untouched by the music's fades
    sfxBus=AC.createGain();sfxBus.gain.value=.8;
    const sLo=AC.createBiquadFilter();sLo.type="highshelf";sLo.frequency.value=8000;sLo.gain.value=-3;
    const sComp=AC.createDynamicsCompressor();sComp.threshold.value=-20;sComp.knee.value=12;sComp.ratio.value=3;sComp.attack.value=.005;sComp.release.value=.25;
    sfxBus.connect(sLo);sLo.connect(sComp);sComp.connect(AC.destination);
    sfxRev=AC.createGain();sfxRev.gain.value=.22;const sConv=AC.createConvolver();sConv.buffer=ir(1.4);sfxRev.connect(sConv);sConv.connect(sfxBus);
  }
  // tenor channel: low-mid warmth, tamed honk, dark top, generous room
  function mkSax(){const g=AC.createGain();g.gain.value=1.3;
    const warm=AC.createBiquadFilter();warm.type="peaking";warm.frequency.value=230;warm.Q.value=.8;warm.gain.value=3.5;
    const honk=AC.createBiquadFilter();honk.type="peaking";honk.frequency.value=1250;honk.Q.value=1.2;honk.gain.value=-2.5;
    const lp=AC.createBiquadFilter();lp.type="lowpass";lp.frequency.value=2600;lp.Q.value=.5;
    const p=AC.createStereoPanner();p.pan.value=.3;const s=AC.createGain();s.gain.value=.62;
    g.connect(warm);warm.connect(honk);honk.connect(lp);lp.connect(p);p.connect(bandBus);lp.connect(s);s.connect(revIn);return g;}
  async function init(){
    ensureCtx();
    master=AC.createGain();master.gain.value=0;
    const lo=AC.createBiquadFilter();lo.type="lowshelf";lo.frequency.value=140;lo.gain.value=2.5;
    const hi=AC.createBiquadFilter();hi.type="highshelf";hi.frequency.value=7000;hi.gain.value=-2.5;
    const sh=AC.createWaveShaper();sh.curve=sat(1.3);sh.oversample="2x";
    const comp=AC.createDynamicsCompressor();comp.threshold.value=-18;comp.knee.value=14;comp.ratio.value=2.5;comp.attack.value=.02;comp.release.value=.3;
    master.connect(lo);lo.connect(hi);hi.connect(sh);sh.connect(comp);comp.connect(AC.destination);
    bandBus=AC.createGain();bandDist=AC.createGain();bandPan=AC.createStereoPanner();bandBus.connect(bandPan);bandPan.connect(bandDist);bandDist.connect(master);
    revIn=AC.createGain();const rev=AC.createConvolver();rev.buffer=ir(3.2);const revOut=AC.createGain();revOut.gain.value=.9;revIn.connect(rev);rev.connect(revOut);revOut.connect(bandBus);
    ch.piano=mkCh(-.28,.34,{gain:.9});ch.bass=mkCh(.05,.1,{lp:1600,gain:1.1});ch.sax=mkSax();ch.drums=mkCh(-.05,.25,{gain:.8});ch.brush=mkCh(.1,.2,{gain:1});Object.keys(ch).forEach(k=>BASE[k]=ch[k].gain.value);applyFeature();
    crowdBus=AC.createGain();crowdBus.gain.value=0;crowdBus.connect(master);
    const data=await (await fetch("samples.json")).json();
    for(const inst of ["piano","bass","sax"]){SAMP[inst]={};await Promise.all(Object.entries(data[inst]).map(async([m,s])=>{SAMP[inst][+m]=await AC.decodeAudioData(b64(s));}));}
    SAMP.drums={};await Promise.all(Object.entries(data.drums).map(async([k,s])=>{SAMP.drums[k]=await AC.decodeAudioData(b64(s));}));
    setupCrowd();loaded=true;
  }
  function ev(t,type,v){evq.push({t,type,v});}
  AUD.drain=function(){const now=AC.currentTime;for(let i=evq.length-1;i>=0;i--){const e=evq[i];if(e.t<=now){if(e.type==="bass")pulse=Math.max(pulse,.9);if(e.type==="drum")drumHit=1;if(e.type==="piano")pianoHit=1;if(e.type==="sax")saxOn=1;evq.splice(i,1);}}};
  const bandPos=new THREE.Vector3(0,2,-5),camRight=new THREE.Vector3();
  AUD.updateSpace=function(){const d=camera.position.distanceTo(bandPos);bandDist.gain.setTargetAtTime(Math.min(1.25,9/Math.max(5,d))+.12,AC.currentTime,.2);
    camRight.setFromMatrixColumn(camera.matrixWorld,0);const dir=bandPos.clone().sub(camera.position).normalize();bandPan.pan.setTargetAtTime(Math.max(-.7,Math.min(.7,dir.dot(camRight)*.8)),AC.currentTime,.2);};
  function play(inst,m,t,vel,dur,dest,o={}){
    const bank=SAMP[inst];let key=null;for(const k in bank){if(key===null||Math.abs(k-m)<Math.abs(key-m))key=+k;}
    const src=AC.createBufferSource();src.buffer=bank[key];src.playbackRate.value=Math.pow(2,(m-key)/12);
    if(o.scoop){src.detune.setValueAtTime(-o.scoop,t);src.detune.linearRampToValueAtTime(0,t+.12);}
    if(o.vib&&dur>.6){const l=AC.createOscillator();l.frequency.value=4.8+Math.random()*.6;const lg=AC.createGain();lg.gain.setValueAtTime(0,t);lg.gain.linearRampToValueAtTime(0,t+dur*.35);lg.gain.linearRampToValueAtTime(o.vib,t+dur*.8);l.connect(lg);lg.connect(src.detune);l.start(t);l.stop(t+dur+1);}
    if(o.fall){src.detune.setValueAtTime(0,t+dur-.1);src.detune.linearRampToValueAtTime(-180,t+dur+.25);}
    const f=AC.createBiquadFilter();f.type="lowpass";f.frequency.value=o.lp||(900+vel*vel*7000);
    const g=AC.createGain(),v=vel*vel*(o.gain||1),rel=o.rel||.4;
    g.gain.setValueAtTime(0,t);g.gain.linearRampToValueAtTime(v,t+(o.att||.006));
    if(o.swell){g.gain.linearRampToValueAtTime(v*.75,t+dur*.4);g.gain.linearRampToValueAtTime(v*1.05,t+dur*.85);}
    g.gain.setValueAtTime(o.swell?v*1.05:v,t+dur);g.gain.exponentialRampToValueAtTime(.0004,t+dur+rel);
    src.connect(f);f.connect(g);g.connect(dest);src.start(t);src.stop(t+dur+rel+.05);}
  // subtone tenor: soft slow attack, dark filter, breath layer riding the envelope,
  // vibrato that only blooms late in long notes; long notes crossfade sample segments
  function saxNote(m,t,vel,dur,o={}){
    const bank=SAMP.sax;let key=null;for(const k in bank){if(key===null||Math.abs(k-m)<Math.abs(key-m))key=+k;}
    const buf=bank[key],rate=Math.pow(2,(m-key)/12),rel=o.rel||.7,att=o.att||.12,end=t+dur+rel;
    const f=AC.createBiquadFilter();f.type="lowpass";f.Q.value=.4;f.frequency.setValueAtTime((o.lp||1400)*.8,t);f.frequency.linearRampToValueAtTime(o.lp||1400,t+att+.25);
    const g=AC.createGain(),v=vel*vel;
    g.gain.setValueAtTime(0,t);g.gain.linearRampToValueAtTime(v*.55,t+att);g.gain.linearRampToValueAtTime(v*.9,t+att+.3);
    if(dur>1.3){g.gain.linearRampToValueAtTime(v*.8,t+dur*.45);g.gain.linearRampToValueAtTime(v,t+dur*.85);}
    g.gain.setValueAtTime(dur>1.3?v:v*.9,t+dur);g.gain.exponentialRampToValueAtTime(.0004,end);
    f.connect(g);g.connect(ch.sax);
    // sample segments (samples last ~3 s): crossfade looped sustain for long notes
    const srcs=[],X=.4,SEG=1.6,OFF=.8,firstLen=2.6;
    const seg=(st,off,len,fadeIn)=>{const s=AC.createBufferSource();s.buffer=buf;s.playbackRate.value=rate;const sg=AC.createGain();
      if(fadeIn){sg.gain.setValueAtTime(0,st);sg.gain.linearRampToValueAtTime(1,st+X);}else sg.gain.setValueAtTime(1,st);
      if(st+len<end){sg.gain.setValueAtTime(1,st+len-X);sg.gain.linearRampToValueAtTime(0,st+len);}
      s.connect(sg);sg.connect(f);s.start(st,off);s.stop(Math.min(end,st+len)+.05);srcs.push(s);};
    seg(t,0,firstLen,false);for(let st=t+firstLen-X;st<end;st+=SEG)seg(st,OFF,SEG+X,true);
    if(o.scoop)srcs.forEach(s=>{s.detune.setValueAtTime(-o.scoop,t);s.detune.linearRampToValueAtTime(0,t+.22);});
    if(o.fall)srcs.forEach(s=>{s.detune.setValueAtTime(0,t+dur-.05);s.detune.linearRampToValueAtTime(-70,end);});
    if(o.vib&&dur>1.4){const l=AC.createOscillator();l.frequency.value=4.2+Math.random()*.5;const lg=AC.createGain();
      lg.gain.setValueAtTime(0,t);lg.gain.setValueAtTime(0,t+dur*.45);lg.gain.linearRampToValueAtTime(o.vib,t+dur*.9);
      l.connect(lg);srcs.forEach(s=>lg.connect(s.detune));l.start(t);l.stop(end+.05);}
    // breath / air: band-limited noise following the note, a small puff on the attack
    const n=AC.createBufferSource();n.buffer=SAMP.noise;n.loop=true;
    const bp=AC.createBiquadFilter();bp.type="bandpass";bp.frequency.value=1500+Math.random()*500;bp.Q.value=.7;
    const hp=AC.createBiquadFilter();hp.type="highpass";hp.frequency.value=800;
    const ng=AC.createGain(),b=v*(o.air||.035);
    ng.gain.setValueAtTime(0,t-.03);ng.gain.linearRampToValueAtTime(b*2.2,t+att*.7);ng.gain.linearRampToValueAtTime(b,t+att+.25);
    ng.gain.setValueAtTime(b,t+dur);ng.gain.exponentialRampToValueAtTime(.00005,t+dur+rel*.7);
    n.connect(bp);bp.connect(hp);hp.connect(ng);ng.connect(ch.sax);n.start(Math.max(0,t-.03),Math.random()*1.5);n.stop(end+.05);}
  function noise(t,dur,{freq=3000,q=.7,type="bandpass",gain=.05,att=.02,dest=ch.brush,sweep=0}={}){const s=AC.createBufferSource();s.buffer=SAMP.noise;const f=AC.createBiquadFilter();f.type=type;f.frequency.setValueAtTime(freq,t);if(sweep)f.frequency.linearRampToValueAtTime(freq+sweep,t+dur);f.Q.value=q;const g=AC.createGain();g.gain.setValueAtTime(0,t);g.gain.linearRampToValueAtTime(gain,t+att);g.gain.exponentialRampToValueAtTime(.0003,t+dur);s.connect(f);f.connect(g);g.connect(dest);s.start(t,Math.random()*1.2);s.stop(t+dur+.05);}
  function ride(t,vel){const base=[2.0,3.02,4.16,5.43,6.79,8.21];const mix=AC.createGain();base.forEach(r=>{const o=AC.createOscillator();o.type="square";o.frequency.value=r*405;o.connect(mix);o.start(t);o.stop(t+3);});
    const bp=AC.createBiquadFilter();bp.type="bandpass";bp.frequency.value=6800;bp.Q.value=.5;const hp=AC.createBiquadFilter();hp.type="highpass";hp.frequency.value=4200;
    const g=AC.createGain();g.gain.setValueAtTime(0,t);g.gain.linearRampToValueAtTime(vel*.03,t+.004);g.gain.exponentialRampToValueAtTime(vel*.008,t+.25);g.gain.exponentialRampToValueAtTime(.0002,t+2.8);
    mix.connect(bp);bp.connect(hp);hp.connect(g);g.connect(ch.drums);noise(t,.12,{freq:9000,q:1,gain:vel*.03,att:.002,dest:ch.drums});}
  function drum(k,t,vel,rate=1){const s=AC.createBufferSource();s.buffer=SAMP.drums[k];s.playbackRate.value=rate;const g=AC.createGain();g.gain.value=vel*vel;const f=AC.createBiquadFilter();f.type="lowpass";f.frequency.value=2500+vel*6000;s.connect(f);f.connect(g);g.connect(ch.drums);s.start(t);}

  // ---------- musicians' state ----------
  let bassPrev=38,voicePrev=null,melPrev=60,pianoMelPrev=74,phraseLeft=0,restLeft=0;
  function nearestPc(target,prev,lo,hi){let best=null;for(let m=lo;m<=hi;m++)if(pc(m)===pc(target)&&(best===null||Math.abs(m-prev)<Math.abs(best-prev)))best=m;return best;}
  function voicing(root,q){const opts=UPPER[q].map(v=>v.map(i=>i+root));let best=null,bd=1e9;
    for(const o of opts)for(let sh=36;sh<=72;sh+=12){const v=o.map(x=>x+sh);if(v[0]<50||v[v.length-1]>74)continue;const c=v.reduce((a,b)=>a+b)/v.length;const d=voicePrev?Math.abs(c-voicePrev):Math.abs(c-61);if(d<bd){bd=d;best=v;}}
    voicePrev=best.reduce((a,b)=>a+b)/best.length;return best;}
  function melodyNote(prev,root,q,strong,lo,hi){const set=(strong?TONES[q]:SCALE[q]).map(i=>pc(i+root));const c=[];for(let m=prev-5;m<=prev+5;m++)if(m>=lo&&m<=hi&&set.includes(pc(m))&&m!==prev)c.push(m);
    if(!c.length)return prev;c.sort((a,b)=>Math.abs(a-prev)-Math.abs(b-prev));const w=c.slice(0,Math.min(3,c.length));return w[Math.random()*w.length|0];}
  const RHY=[ // [pos,dur] in beats for a melodic bar
    [[0,1.5],[1.5,.5],[2,2]], [[0,3],[3,.5],[3.5,.5]], [[.6,.4],[1,1],[2,1.5],[3.5,.5]], [[0,2],[2,1],[3,1]], [[1,1],[2,.6],[2.6,.4],[3,1]], [[0,4]], [[0,1],[1,1],[2,2]]
  ];

  const SAX_RHY=[ // lyrical: long tones, pickups, space
    [[0,3]], [[0,2],[2,2]], [[.5,1.5],[2,2]], [[0,1.5],[1.5,.5],[2,2]], [[1,3]], [[0,2.5],[3,1]], [[0,1],[1,3]], [[0,4]], [[2,2]]
  ];
  function scheduleBar(barN,t){
    const bar=barN%16, chorus=Math.floor(barN/16)%3, lead=chorus===1?"piano":"sax";
    const segs=FORM[bar];
    // ---- bass: two-feel with occasional walking in the second half ----
    const walk=chorus===2&&bar>=8;
    for(let b=0;b<4;b+=walk?1:2){
      const c=chordAt(bar,b), nextC=b+(walk?1:2)>=4?chordAt(barN+1,0):chordAt(bar,b+(walk?1:2));
      let m;if(b===c.start)m=nearestPc(c.root,bassPrev,31,50);
      else if(Math.random()<.5)m=nearestPc(nextC.root,bassPrev,31,50)+(Math.random()<.5?1:-1);
      else m=nearestPc(c.root+7,bassPrev,31,50);
      bassPrev=m;const dur=(walk?1:2)*SPB*.96;
      play("bass",m,t+b*SPB+(Math.random()*.012),.78+Math.random()*.1,dur,ch.bass,{rel:.25,lp:1500});ev(t+b*SPB,"bass");
    }
    // ---- brushes ----
    for(let b=0;b<4;b++){const tb=t+b*SPB;
      noise(tb,SPB*.95,{freq:2600,q:.9,gain:.022+(b%2)*.008,att:SPB*.45,sweep:900});
      if(b%2===1){drum("snare",tb,.26+Math.random()*.06,.95);noise(tb,.25,{freq:4000,q:.6,gain:.03,att:.003});drum("hihat",tb+.01,.16,.8);ev(tb,"drum");}
      if(b===0&&Math.random()<.5)drum("kick",tb,.22);
      if(Math.random()<.18)drum("snare",tb+SW*SPB,.12,1.05);
    }
    if(bar===0)ride(t,.9);
    if(bar===15){[2,2.33,2.66,3,3.33,3.66].forEach((p,i)=>drum(i<3?"snare":"tom1",t+p*SPB,.18+i*.03,i<3?1:.8-i*.03));}
    // ---- piano: rolled voicings, LH root + 7th ----
    segs.forEach((s,si)=>{const start=segs.slice(0,si).reduce((a,x)=>a+x[2],0), ts=t+start*SPB;
      const v=voicing(s[0],s[1]);const lh=nearestPc(s[0],45,38,50);const lhs=[lh,lh+(TONES[s[1]][3]||10)];
      const vel=lead==="piano"?.42:.5;
      lhs.forEach((m,i)=>play("piano",m,ts+i*.035,vel+.05,s[2]*SPB*.98,ch.piano,{rel:1.2}));
      v.forEach((m,i)=>play("piano",m,ts+.09+i*.045+Math.random()*.01,vel+Math.random()*.06,s[2]*SPB*.98,ch.piano,{rel:1.4}));ev(ts,"piano");
      if(s[2]===4&&Math.random()<.45&&lead==="sax"){const again=v.slice(1);again.forEach((m,i)=>play("piano",m+(i===again.length-1&&Math.random()<.5?2:0),ts+2.6*SPB+i*.03,.34,1.2*SPB,ch.piano,{rel:1}));}
    });
    // ---- lead melody ----
    if(restLeft>0){restLeft--;if(lead==="sax")pianoFill(barN,t);return;}
    if(phraseLeft<=0)phraseLeft=2+(Math.random()<.4?1:0);
    const rh=lead==="sax"?SAX_RHY[Math.random()*SAX_RHY.length|0]:RHY[Math.random()*RHY.length|0];const last=phraseLeft===1;
    rh.forEach(([pos,dur],i)=>{const c=chordAt(bar,pos),strong=pos%1===0;
      const tt=t+(pos%1?Math.floor(pos)+(pos%1>=.5?SW:pos%1):pos)*SPB;
      if(lead==="sax"){let n=melodyNote(melPrev,c.root,c.q,strong,50,67);const fin=last&&i===rh.length-1;if(fin){n=nearestPc(c.root+TONES[c.q][1+(Math.random()*3|0)],n,50,67);}melPrev=n;
        const d=(fin?Math.max(dur,2.5):dur)*SPB*.97, vel=.5+Math.random()*.1-(strong?0:.04);
        saxNote(n,tt+Math.random()*.04,vel,d,{att:.1+Math.random()*.06,rel:.7+(fin?.4:0),vib:11,scoop:strong&&Math.random()<.15?40:0,fall:fin&&Math.random()<.15,lp:1150+vel*vel*1200+Math.random()*200});ev(tt,"sax");}
      else {let n=melodyNote(pianoMelPrev,c.root,c.q,strong,67,86);pianoMelPrev=n;play("piano",n,tt,.62+Math.random()*.12,dur*SPB,ch.piano,{rel:1.2});if(strong&&Math.random()<.5)play("piano",n-12,tt+.01,.4,dur*SPB,ch.piano,{rel:1});ev(tt,"piano");}
    });
    phraseLeft--;if(phraseLeft<=0)restLeft=Math.random()<.6?1:0;
  }
  function pianoFill(barN,t){const bar=barN%16;const c=chordAt(bar,2);let n=pianoMelPrev;[2,2.5,3,3.5].forEach((p,i)=>{if(Math.random()<.25)return;const cc=chordAt(bar,p);n=melodyNote(n,cc.root,cc.q,i%2===0,70,86);play("piano",n,t+(p%1?Math.floor(p)+SW:p)*SPB,.4+Math.random()*.1,.8*SPB,ch.piano,{rel:1});});pianoMelPrev=n;}

  // ---------- crowd ambience ----------
  const voices=[];
  function setupCrowd(){for(let i=0;i<7;i++){const s=AC.createBufferSource();s.buffer=SAMP.noise;s.loop=true;const f=AC.createBiquadFilter();f.type="bandpass";f.frequency.value=500+Math.random()*500;f.Q.value=5;const f2=AC.createBiquadFilter();f2.type="lowpass";f2.frequency.value=2200;
      const g=AC.createGain();g.gain.value=0;const p=AC.createStereoPanner();p.pan.value=Math.random()*1.6-.8;s.connect(f);f.connect(f2);f2.connect(g);g.connect(p);p.connect(crowdBus);s.start();voices.push({f,g,next:0});}}
  function crowdTick(now){voices.forEach(v=>{if(now+.2>v.next){const t=Math.max(now,v.next),d=.08+Math.random()*.22;v.g.gain.setTargetAtTime(Math.random()<.2?0:.05+Math.random()*.08,t,.02);v.g.gain.setTargetAtTime(0,t+d,.04);v.f.frequency.setTargetAtTime(380+Math.random()*700,t,.03);v.next=t+d+.03+Math.random()*(Math.random()<.15?1.2:.12);}});
    if(Math.random()<.004){const t=now+.1;[2637,3516,5280].forEach((f,i)=>{const o=AC.createOscillator();o.frequency.value=f*(1+Math.random()*.01);const g=AC.createGain();g.gain.setValueAtTime(.012/(i+1),t);g.gain.exponentialRampToValueAtTime(.0001,t+.6);const p=AC.createStereoPanner();p.pan.value=Math.random()*1.6-.8;o.connect(g);g.connect(p);p.connect(crowdBus);o.start(t);o.stop(t+.7);});}}

  let nextBarT=0,barN=0;
  function tick(){const now=AC.currentTime;while(nextBarT<now+.4){scheduleBar(barN,nextBarT);nextBarT+=4*SPB;barN++;}crowdTick(now);}
  AUD.start=async function(){
    if(!loaded){if(!loading)loading=init();await loading;}
    await AC.resume();
    master.gain.cancelScheduledValues(AC.currentTime);master.gain.setValueAtTime(master.gain.value,AC.currentTime);master.gain.linearRampToValueAtTime(.9,AC.currentTime+1.2);
    crowdBus.gain.setTargetAtTime(.55,AC.currentTime,.8);
    nextBarT=AC.currentTime+.15;barN=0;phraseLeft=0;restLeft=1;voicePrev=null;melPrev=60;
    timer=setInterval(tick,40);AUD.playing=true;
  };
  // ---------- sound effects for stall interactions (own bus, never faded by the music) ----------
  let crackleBuf=null;
  function crackle(){if(crackleBuf)return crackleBuf;const sr=AC.sampleRate,len=Math.floor(sr*3),b=AC.createBuffer(1,len,sr),d=b.getChannelData(0);
    for(let i=0;i<len;){i+=Math.floor(sr*(.002+Math.random()*Math.random()*.03));const a=(Math.random()**2.5)*(Math.random()<.06?1:.35),dl=Math.floor(sr*(.0006+Math.random()*.004));
      for(let j=0;j<dl&&i+j<len;j++)d[i+j]+=a*(Math.random()*2-1)*Math.exp(-5*j/dl);}
    return crackleBuf=b;}
  function sOut(pan=0,rev=1){const p=AC.createStereoPanner();p.pan.value=pan;p.connect(sfxBus);if(rev){const s=AC.createGain();s.gain.value=rev;p.connect(s);s.connect(sfxRev);}return p;}
  function sNoise(t,dur,dest,{type="bandpass",f=1000,f2=0,q=.7,off=Math.random()*1.5,buf=SAMP.noise}={}){const s=AC.createBufferSource();s.buffer=buf;s.loop=true;const fl=AC.createBiquadFilter();fl.type=type;fl.frequency.setValueAtTime(f,t);if(f2)fl.frequency.exponentialRampToValueAtTime(f2,t+dur);fl.Q.value=q;const g=AC.createGain();s.connect(fl);fl.connect(g);g.connect(dest);s.start(t,off%buf.duration);s.stop(t+dur+.05);return g.gain;}
  function sTone(t,freq,amp,dec,dest,{att=.002,type="sine",det=0}={}){const o=AC.createOscillator();o.type=type;o.frequency.value=freq;o.detune.value=det;const g=AC.createGain();g.gain.setValueAtTime(0,t);g.gain.linearRampToValueAtTime(amp,t+att);g.gain.exponentialRampToValueAtTime(.00005,t+att+dec);o.connect(g);g.connect(dest);o.start(t);o.stop(t+att+dec+.05);return o;}
  function env(p,t,pts){p.setValueAtTime(0,t);pts.forEach(([dt,v])=>p.linearRampToValueAtTime(v,t+dt));}
  const SFX={
    clink(t){const out=sOut((Math.random()-.5)*.4,.8);
      // two thick glass mugs: short tick + two inharmonic rings slightly apart
      const tick=sNoise(t,.03,out,{type:"highpass",f:3500,q:.5});tick.setValueAtTime(0,t);tick.linearRampToValueAtTime(.05,t+.001);tick.exponentialRampToValueAtTime(.0001,t+.025);
      [[1870,0],[2140,.004]].forEach(([f0,dt],k)=>{f0*=1+Math.random()*.03;[[1,.03,.5],[2.37,.018,.28],[4.1,.009,.14],[6.3,.004,.07]].forEach(([r,a,d])=>sTone(t+dt,f0*r,a*(k?.8:1),d,out));});},
    pour(t){const out=sOut(.1,.5),D=1.9;
      // tap stream: gurgling band noise whose resonance rises as the glass fills
      const st=sNoise(t,D+.2,out,{f:520,f2:1250,q:2.2});env(st,t,[[.12,.05],[D-.2,.045],[D,0]]);
      for(let k=0;k<22;k++){const tt=t+.1+Math.random()*(D-.3);st.setValueAtTime(.03+Math.random()*.025,tt);}
      const body=sNoise(t,D+.2,out,{type:"lowpass",f:380,q:.6});env(body,t,[[.1,.035],[D-.2,.03],[D,0]]);
      // bubbles: tiny rising blips
      for(let k=0;k<16;k++){const tt=t+.15+Math.random()*(D-.3),f0=500+Math.random()*700,o=sTone(tt,f0,.012,.04,out);o.frequency.setValueAtTime(f0,tt);o.frequency.exponentialRampToValueAtTime(f0*1.7,tt+.04);}
      // foam fizz: fine crackle building up and lingering after the tap closes
      const fz=sNoise(t,D+1.2,out,{type:"highpass",f:5500,q:.4,buf:crackle()});fz.setValueAtTime(0,t);fz.linearRampToValueAtTime(.05,t+D*.7);fz.linearRampToValueAtTime(.07,t+D);fz.exponentialRampToValueAtTime(.0005,t+D+1.15);},
    sizzle(t){const out=sOut(-.15,.3),D=2.5;
      const bed=sNoise(t,D,out,{f:5200,q:.5});bed.setValueAtTime(0,t);bed.linearRampToValueAtTime(.022,t+.2);for(let k=1;k<10;k++)bed.linearRampToValueAtTime(.014+Math.random()*.014,t+.2+k*(D-.8)/9);bed.linearRampToValueAtTime(0,t+D);
      const cr=sNoise(t,D,out,{type:"highpass",f:2200,q:.5,buf:crackle()});cr.setValueAtTime(0,t);cr.linearRampToValueAtTime(.12,t+.12);cr.setValueAtTime(.12,t+D-.7);cr.linearRampToValueAtTime(0,t+D);
      // a few fat spits
      for(let k=0;k<5;k++){const tt=t+.2+Math.random()*(D-.6),sp=sNoise(tt,.08,out,{f:900+Math.random()*900,q:1.5});sp.setValueAtTime(0,tt);sp.linearRampToValueAtTime(.05,tt+.003);sp.exponentialRampToValueAtTime(.0002,tt+.07);}},
    page(t){const out=sOut((Math.random()-.5)*.3,.4),D=.42;
      const sw=sNoise(t,D,out,{f:1300,f2:3800,q:1.1});sw.setValueAtTime(0,t);
      for(let k=1;k<=9;k++)sw.linearRampToValueAtTime((k<7?.012+k*.004:.04-(k-6)*.012)*(0.7+Math.random()*.6),t+k*D/10);sw.linearRampToValueAtTime(0,t+D);
      const cr=sNoise(t+.05,.25,out,{type:"highpass",f:3000,q:.5,buf:crackle()});cr.setValueAtTime(0,t+.05);cr.linearRampToValueAtTime(.05,t+.15);cr.linearRampToValueAtTime(0,t+.3);
      const flap=sNoise(t+D-.06,.12,out,{type:"lowpass",f:500,q:.7});flap.setValueAtTime(0,t+D-.06);flap.linearRampToValueAtTime(.06,t+D-.04);flap.exponentialRampToValueAtTime(.0002,t+D+.08);},
    chime(t){const out=sOut((Math.random()-.5)*.5,1.2),N=[79,83,84,86,88,91],a=N[Math.random()*N.length|0],b=N[Math.random()*N.length|0];
      [[a,0,1],[b,.16,.7]].forEach(([m,dt,s])=>{const f=440*Math.pow(2,(m-69)/12),tt=t+dt;sTone(tt,f,.035*s,1.6,out);sTone(tt,f*2,.008*s,.5,out);sTone(tt,f*5.4,.004*s,.12,out);});},
    whoosh(t){const p=AC.createStereoPanner();p.pan.setValueAtTime(-.6,t);p.pan.linearRampToValueAtTime(.6,t+1.6);p.connect(sfxBus);const s=AC.createGain();s.gain.value=.5;p.connect(s);s.connect(sfxRev);
      const w=sNoise(t,1.7,p,{f:280,f2:900,q:1.3});env(w,t,[[.65,.07],[1.65,0]]);
      const w2=sNoise(t,1.7,p,{type:"lowpass",f:260,q:.5});env(w2,t,[[.7,.04],[1.65,0]]);}
  };
  const BASE={};let featured=null;
  function applyFeature(){if(!AC||!ch.piano)return;const now=AC.currentTime;Object.keys(ch).forEach(k=>{const on=featured&&(k===featured||(featured==="drums"&&k==="brush"));const f=!featured?1:on?1.7:.55;ch[k].gain.setTargetAtTime(BASE[k]*f,now,.4);});}
  AUD.feature=function(name){featured=name||null;applyFeature();};
  AUD.sfx=function(name){try{ensureCtx();}catch(e){return;}const fn=SFX[name];if(!fn)return;
    const go=()=>{const t=AC.currentTime+.02;fn(t);sfxUntil=Math.max(sfxUntil,t+3.5);
      if(!AUD.playing)setTimeout(()=>{if(!AUD.playing&&AC.state==="running"&&AC.currentTime>sfxUntil)AC.suspend();},4000);};
    if(AC.state!=="running")return AC.resume().then(go,()=>{});go();};
  AUD.stop=function(){if(!AC)return;master.gain.cancelScheduledValues(AC.currentTime);master.gain.setValueAtTime(master.gain.value,AC.currentTime);master.gain.linearRampToValueAtTime(0,AC.currentTime+.8);clearInterval(timer);timer=null;AUD.playing=false;evq.length=0;setTimeout(()=>{if(!AUD.playing&&AC.currentTime>sfxUntil)AC.suspend();},1000);};
})();

