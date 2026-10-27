// 用法：node render.js [scene.html] [out.mp4]        逐帧截图 → ffmpeg
//       node render.js scene.html --stills 0,225,449  只导出指定帧为 PNG（检查用）
const {chromium}=require('playwright'),{spawn}=require('child_process'),path=require('path'),fs=require('fs'),{pathToFileURL}=require('url');
(async()=>{const scene=process.argv[2]||'scene.html',arg=process.argv[3]||'silent.mp4';
 const b=await chromium.launch({channel:process.env.PW_CHANNEL||(process.platform==='win32'?'msedge':undefined)}),pg=await b.newPage({viewport:{width:1080,height:1080}});
 await pg.goto(pathToFileURL(path.resolve(scene)).href);
 await pg.evaluate(()=>document.fonts.ready);
 const {N,FPS,META}=await pg.evaluate(()=>({N:window.N,FPS:window.FPS,META:window.META||null}));
 if(META)fs.writeFileSync('meta.json',JSON.stringify(META));   // 给 audio.py 对齐音效用
 const grab=i=>pg.evaluate(i=>{frame(i);return document.getElementById('c').toDataURL('image/png')},i).then(d=>Buffer.from(d.split(',')[1],'base64'));
 if(arg==='--stills'){for(const i of process.argv[4].split(',').map(Number))fs.writeFileSync(`still_${i}.png`,await grab(i));await b.close();return}
 const ff=spawn('ffmpeg',['-y','-loglevel','error','-f','image2pipe','-framerate',String(FPS),'-i','-','-c:v','libx264','-pix_fmt','yuv420p','-crf','17','-preset','slow',arg],{stdio:['pipe','inherit','inherit']});
 const t0=Date.now();
 for(let i=0;i<N;i++){if(!ff.stdin.write(await grab(i)))await new Promise(r=>ff.stdin.once('drain',r));
  if(i%60==0)console.log(`frame ${i}/${N}  ${((Date.now()-t0)/1000).toFixed(1)}s`)}
 ff.stdin.end();await new Promise(r=>ff.on('close',r));await b.close();console.log('done',arg)})();
