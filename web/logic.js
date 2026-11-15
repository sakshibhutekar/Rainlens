(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.RainLensLogic = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  const stops = [[1,190,255],[35,120,240],[30,190,130],[250,225,45],[250,135,35],[235,50,55],[175,55,220]];
  function mix(a,b,t){ return a.map((v,i)=>Math.round(v+(b[i]-v)*t)); }
  function colorFor(mm) {
    if (!Number.isFinite(mm) || mm < 0.2) return [0,0,0,0];
    const levels=[1,2.5,5,10,25,50];
    if(mm<1) return [175,220,255,170];
    let i=levels.findIndex(x=>mm<=x); if(i<0)i=levels.length-1;
    const lo=i===0?1:levels[i-1], t=Math.max(0,Math.min(1,(mm-lo)/(levels[i]-lo)));
    return [...mix(stops[i],stops[i+1],t),190];
  }
  function diffColorFor(d) {
    if(!Number.isFinite(d)||Math.abs(d)<2)return [0,0,0,0];
    const x=Math.min(1,(Math.abs(d)-2)/23);
    return d>0?[Math.round(255-55*x),Math.round(185-150*x),Math.round(190-155*x),190]:[Math.round(180-150*x),Math.round(215-100*x),255,190];
  }
  function classify(mm){ return mm<2.5?"Light":mm<10?"Moderate":mm<=25?"Heavy":"Very heavy"; }
  function summarize(values,times,otherValues,modelName="IFS",otherModelName="AIFS",displayName=modelName){
    const vals=Array.from(values||[],Number), total=vals.reduce((a,b)=>a+b,0);
    if(total<1)return `${displayName}: No significant rain expected in the next 6 days.`;
    let best=null, start=-1;
    for(let i=0;i<=vals.length;i++){
      if(i<vals.length&&vals[i]>=0.2){if(start<0)start=i;continue;}
      if(start>=0){const sum=vals.slice(start,i).reduce((a,b)=>a+b,0);if(!best||sum>best.total)best={start,end:i-1,total:sum,peak:Math.max(...vals.slice(start,i))};start=-1;}
    }
    const fmt=(idx,offsetHours=0)=>{
      const d=new Date(new Date(times[idx]).getTime()+offsetHours*3600000);
      const day=d.toLocaleDateString("en-IN",{timeZone:"Asia/Kolkata",weekday:"long",day:"numeric",month:"short"});
      const today=new Date().toLocaleDateString("en-CA",{timeZone:"Asia/Kolkata"});
      const tomorrow=new Date(Date.now()+86400000).toLocaleDateString("en-CA",{timeZone:"Asia/Kolkata"});
      const target=d.toLocaleDateString("en-CA",{timeZone:"Asia/Kolkata"});
      const named=target===today?"today":target===tomorrow?"tomorrow":day;
      return {day:named,time:d.toLocaleTimeString("en-IN",{timeZone:"Asia/Kolkata",hour:"numeric",minute:"2-digit",hour12:true}).replace(" ","")};
    };
    const a=fmt(best.start,-6), b=fmt(best.end), duration=(best.end-best.start+1)*6;
    let msg=`${classify(best.peak)} rain expected between ${a.time} ${a.day} and ${b.time} ${b.day} (about ${Math.round(best.total)} mm over ${duration} hours; peak 6-hour amount ${Math.round(best.peak)} mm). Total over 6 days: ${Math.round(total)} mm.`;
    if(otherValues){const other=Array.from(otherValues,Number).reduce((x,y)=>x+y,0);if(Math.max(total,other)>2*Math.min(total,other)&&Math.abs(total-other)>10){const ifsTotal=modelName==="IFS"?total:other,aifsTotal=modelName==="AIFS"?total:other;msg+=` IFS and AIFS disagree here: IFS ${Math.round(ifsTotal)} mm vs AIFS ${Math.round(aifsTotal)} mm.`;}}
    return `${displayName}: ${msg}`;
  }
  return {colorFor,diffColorFor,classify,summarize};
});
