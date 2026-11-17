/* UI enhancement layer. It purposefully has no dependency on the legacy business renderer. */
(()=>{
  'use strict';
  const $=(selector,root=document)=>root.querySelector(selector);
  const $$=(selector,root=document)=>[...root.querySelectorAll(selector)];
  const DAY=86400000;
  const pad=value=>String(value).padStart(2,'0');
  const iso=date=>`${date.getFullYear()}-${pad(date.getMonth()+1)}-${pad(date.getDate())}`;
  const fromIso=value=>value?new Date(`${value}T12:00:00`):null;
  const sameDay=(a,b)=>a&&b&&iso(a)===iso(b);
  const inRange=(date,start,end)=>start&&end&&date>=start&&date<=end;
  const addDays=(date,days)=>new Date(date.getFullYear(),date.getMonth(),date.getDate()+days,12);
  const rangeLabel=(start,end)=>start?`${start.getFullYear()}/${pad(start.getMonth()+1)}/${pad(start.getDate())}${end&&!sameDay(start,end)?` — ${end.getFullYear()}/${pad(end.getMonth()+1)}/${pad(end.getDate())}`:''}`:'选择日期范围';

  function pairFor(input){
    const pairs={launchDate:'endDate',endDate:'launchDate',dailyFrom:'dailyTo',dailyTo:'dailyFrom',start_date:'end_date',end_date:'start_date',startDate:'endDate',endDate:'startDate'};
    const key=input.id||input.dataset.f||input.dataset.dashboard||'';
    const partner=pairs[key];
    if(!partner)return [input];
    const scope=input.closest('dialog,section,form,.metric-view')||document;
    const find=()=>input.dataset.f?scope.querySelector(`[data-f="${partner}"]`):input.dataset.dashboard?scope.querySelector(`[data-dashboard="${partner}"]`):scope.querySelector(`#${partner}`);
    const other=find();
    return /end|to$/i.test(key)?[other,input].filter(Boolean):[input,other].filter(Boolean);
  }

  let activeInputs=[];
  let draftStart=null;
  let draftEnd=null;
  let visibleMonth=new Date(new Date().getFullYear(),new Date().getMonth(),1,12);
  let selectedPreset='';
  const picker=document.createElement('dialog');
  picker.id='ekkoDateRangePicker';
  picker.className='ekko-date-picker';
  picker.setAttribute('aria-label','选择日期范围');
  picker.innerHTML='<div class="ekko-date-picker-shell"><div class="ekko-date-picker-head"><strong class="ekko-date-picker-summary"></strong><button class="ekko-date-picker-close" type="button" aria-label="关闭日期选择">关闭</button></div><div class="ekko-date-picker-body"><aside class="ekko-date-presets" aria-label="快捷日期"></aside><section class="ekko-date-calendars" aria-label="日期日历"></section></div><div class="ekko-date-picker-footer"><button type="button" class="soft" data-date-cancel>取消</button><button type="button" class="ekko-date-apply" data-date-apply>应用</button></div></div>';

  const presets=[
    ['today','今天'],['yesterday','昨天'],['last7','近 7 天'],['last30','近 30 天'],['month','本月'],['lastMonth','上月']
  ];
  function presetRange(key){
    const now=new Date(); const today=new Date(now.getFullYear(),now.getMonth(),now.getDate(),12);
    if(key==='today')return [today,today];
    if(key==='yesterday'){const yesterday=addDays(today,-1);return [yesterday,yesterday]}
    if(key==='last7')return [addDays(today,-6),today];
    if(key==='last30')return [addDays(today,-29),today];
    if(key==='month')return [new Date(today.getFullYear(),today.getMonth(),1,12),new Date(today.getFullYear(),today.getMonth()+1,0,12)];
    return [new Date(today.getFullYear(),today.getMonth()-1,1,12),new Date(today.getFullYear(),today.getMonth(),0,12)];
  }
  function renderPresets(){
    const host=$('.ekko-date-presets',picker);
    host.innerHTML=presets.map(([key,label])=>`<button type="button" data-preset="${key}" class="${selectedPreset===key?'is-active':''}">${label}</button>`).join('');
  }
  function calendar(month,index){
    const year=month.getFullYear(),monthIndex=month.getMonth();
    const first=new Date(year,monthIndex,1,12),last=new Date(year,monthIndex+1,0,12);
    const gridStart=addDays(first,-first.getDay());
    const dates=Array.from({length:42},(_,i)=>addDays(gridStart,i));
    const monthName=`${year} 年 ${monthIndex+1} 月`;
    return `<section class="ekko-calendar"><div class="ekko-calendar-header"><button type="button" class="ekko-calendar-nav" data-shift="${index===0?-1:0}" aria-label="上个月">‹</button><strong>${monthName}</strong><button type="button" class="ekko-calendar-nav" data-shift="${index===1?1:0}" aria-label="下个月">›</button></div><div class="ekko-calendar-week"><span>日</span><span>一</span><span>二</span><span>三</span><span>四</span><span>五</span><span>六</span></div><div class="ekko-calendar-grid">${dates.map(date=>{
      const outside=date.getMonth()!==monthIndex;
      const classes=['ekko-calendar-day',outside?'is-outside':'',inRange(date,draftStart,draftEnd)?'is-range':'',sameDay(date,draftStart)?'is-start':'',sameDay(date,draftEnd)?'is-end':''].filter(Boolean).join(' ');
      return `<button type="button" class="${classes}" data-date="${iso(date)}" aria-label="${iso(date)}">${date.getDate()}</button>`;
    }).join('')}</div></section>`;
  }
  function renderPicker(){
    $('.ekko-date-picker-summary',picker).textContent=rangeLabel(draftStart,draftEnd);
    $('.ekko-date-calendars',picker).innerHTML=calendar(visibleMonth,0)+calendar(new Date(visibleMonth.getFullYear(),visibleMonth.getMonth()+1,1,12),1);
    renderPresets();
  }
  function openPicker(input){
    activeInputs=pairFor(input);
    draftStart=fromIso(activeInputs[0]?.value)||fromIso(activeInputs[1]?.value)||null;
    draftEnd=fromIso(activeInputs[1]?.value)||draftStart;
    if(draftStart&&draftEnd&&draftEnd<draftStart)[draftStart,draftEnd]=[draftEnd,draftStart];
    visibleMonth=new Date((draftStart||new Date()).getFullYear(),(draftStart||new Date()).getMonth(),1,12);
    selectedPreset=''; renderPicker();
    if(!picker.open)picker.showModal();
    $('.ekko-date-picker-close',picker).focus();
  }
  function applyPicker(){
    const start=draftStart?iso(draftStart):'';
    const end=(draftEnd||draftStart)?iso(draftEnd||draftStart):'';
    if(activeInputs[0]){activeInputs[0].value=start;activeInputs[0].dispatchEvent(new Event('input',{bubbles:true}));activeInputs[0].dispatchEvent(new Event('change',{bubbles:true}))}
    if(activeInputs[1]){activeInputs[1].value=end;activeInputs[1].dispatchEvent(new Event('input',{bubbles:true}));activeInputs[1].dispatchEvent(new Event('change',{bubbles:true}))}
    picker.close();
  }
  function chooseDate(value){
    const date=fromIso(value);
    if(!draftStart||draftEnd){draftStart=date;draftEnd=null}
    else if(date<draftStart){draftEnd=draftStart;draftStart=date}
    else draftEnd=date;
    selectedPreset='';renderPicker();
  }
  picker.addEventListener('click',event=>{
    const preset=event.target.closest('[data-preset]');
    const day=event.target.closest('[data-date]');
    const shift=event.target.closest('[data-shift]');
    if(preset){[draftStart,draftEnd]=presetRange(preset.dataset.preset);selectedPreset=preset.dataset.preset;visibleMonth=new Date(draftStart.getFullYear(),draftStart.getMonth(),1,12);renderPicker()}
    else if(day)chooseDate(day.dataset.date);
    else if(shift){visibleMonth=new Date(visibleMonth.getFullYear(),visibleMonth.getMonth()+Number(shift.dataset.shift),1,12);renderPicker()}
    else if(event.target.closest('[data-date-cancel],.ekko-date-picker-close'))picker.close();
    else if(event.target.closest('[data-date-apply]'))applyPicker();
  });
  picker.addEventListener('cancel',event=>{event.preventDefault();picker.close()});

  function initialise(){
    document.body.append(picker);
    const duplicateTimestamp=/^(\d{4}-\d{2}-\d{2}\s*[·•]\s*\d{2}:\d{2}:\d{2})\s+\1$/;
    const normalizeTimestamps=root=>{
      const elements=root instanceof Element?[root,...root.querySelectorAll('*')]:[...(root?.querySelectorAll?.('*')||[])];
      elements.forEach(element=>{
        if(element.children.length)return;
        const text=(element.textContent||'').trim();
        const match=text.match(duplicateTimestamp);
        if(match)element.textContent=match[1];
      });
      // Legacy cards are rendered by more than one module.  When two leaf
      // nodes carry the same full creation timestamp, keep the first one only.
      // Distinct dates (for example an "已使用" date) are left untouched.
      const cards=root instanceof Element&&root.matches('.card')?[root]:[...(root?.querySelectorAll?.('.card')||[])];
      cards.forEach(card=>{
        const seen=new Set();
        [...card.querySelectorAll('*')].forEach(element=>{
          if(element.children.length)return;
          const text=(element.textContent||'').trim();
          if(!/^\d{4}-\d{2}-\d{2}\s*[·•]\s*\d{2}:\d{2}(?::\d{2})?$/.test(text))return;
          if(seen.has(text))element.remove();else seen.add(text);
        });
      });
    };
    const decorate=root=>{
      $$('#homeView,#listView,.business-view,[data-business-view]',root).forEach(node=>node.classList.add('ekko-ui-page'));
      $$('.tools',root).forEach(node=>node.classList.add('ekko-ui-filterbar'));
      normalizeTimestamps(root);
    };
    decorate(document);
    new MutationObserver(records=>records.forEach(record=>record.addedNodes.forEach(node=>{if(node.nodeType===1)decorate(node)}))).observe(document.body,{childList:true,subtree:true});
    document.addEventListener('pointerdown',event=>{
      const input=event.target.closest('input[type="date"]');
      if(!input||input.closest('#ekkoDateRangePicker')||input.disabled)return;
      event.preventDefault();event.stopImmediatePropagation();openPicker(input);
    },true);
    document.addEventListener('keydown',event=>{
      const input=event.target.closest?.('input[type="date"]');
      if(!input||input.closest('#ekkoDateRangePicker'))return;
      if(event.key==='Enter'||event.key===' '){event.preventDefault();openPicker(input)}
    },true);
    const keepPageStill=()=>{
      if(!document.body.hasAttribute('data-scroll-locked'))return;
      let fix=document.getElementById('scrollLockFix');
      if(!fix){fix=document.createElement('style');fix.id='scrollLockFix';}
      document.head.append(fix);
      fix.textContent='html{overflow-y:scroll!important;scrollbar-gutter:stable!important}body[data-scroll-locked]{overflow:visible!important;padding-left:0!important;padding-right:0!important;margin-left:0!important;margin-right:0!important;width:auto!important}';
    };
    new MutationObserver(keepPageStill).observe(document.body,{attributes:true,attributeFilter:['data-scroll-locked']});
    requestAnimationFrame(()=>document.documentElement.classList.add('ekko-ui-ready'));
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',initialise,{once:true});else initialise();
})();
