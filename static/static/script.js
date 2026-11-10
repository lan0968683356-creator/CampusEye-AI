const $ = (selector) => document.querySelector(selector);
const fmt = new Intl.DateTimeFormat('zh-TW', {month:'long', day:'numeric', weekday:'long'});
$('#today').textContent = fmt.format(new Date());
let mode = 'stopped';
let chart;

function showFeedback(message, error=false) {
  $('#feedback').textContent = message;
  $('#feedback').style.color = error ? '#df6b68' : '#7091b4';
}
async function api(url, options={}) {
  const res = await fetch(url, {...options, headers:{'Content-Type':'application/json'}, cache:'no-store'});
  const data = await res.json();
  if(!res.ok || data.ok === false) throw new Error(data.message || `請求失敗 (${res.status})`);
  return data;
}
function setVideo(active) {
  const img = $('#video'), placeholder = $('#cameraPlaceholder');
  if (active) {
    if (img.hidden) img.src = '/api/video?time=' + Date.now();
    img.hidden = false; placeholder.hidden = true;
  } else { img.hidden = true; img.removeAttribute('src'); placeholder.hidden = false; }
}
function renderStatus(s) {
  const count = s.count;
  const pill = $('#modePill');
  mode = s.mode;
  $('#detectorInfo').textContent = '偵測引擎：' + (s.detector || '未知');
  pill.className = 'pill ' + (['camera','video'].includes(mode)?'real':mode==='stopped'?'off':'');
  pill.textContent = mode==='camera'?'● 攝影機運作中':mode==='video'?'● 影片分析中':mode==='demo'?'● 示範模式 · 模擬資料':'○ 系統已停止';
  $('#liveChip').innerHTML = `<span class="pulse"></span> ${mode==='camera'?'LIVE':mode==='video'?'VIDEO':mode==='demo'?'DEMO':'OFF'}`;
  $('#currentCount').textContent = s.running ? count : '—';
  $('#limitCount').textContent = s.threshold;
  $('#ringValue').textContent = s.running ? count : '—';
  if(document.activeElement !== $('#threshold')) $('#threshold').value = s.threshold;
  $('#lastUpdate').textContent = '更新時間 ' + new Date().toLocaleTimeString('zh-TW', {hour:'2-digit',minute:'2-digit',second:'2-digit'});
  if(['camera','video'].includes(mode)) setVideo(true); else setVideo(false);
  if(!s.running) {
    const completed = mode === 'stopped' && (s.message || '').includes('影片分析完成');
    $('#insightTitle').textContent = completed ? '影片分析已完成' : '尚未開始監測';
    $('#insightBody').textContent = completed
      ? '分析已結束，可查看今日平均、最高人數與提醒紀錄。'
      : '啟動攝影機或示範模式以取得資料。';
    $('#recommendation').textContent = '系統僅提供匿名統計；現場狀況仍須由人員確認。';
  } else if (count >= s.threshold) {
    $('#insightTitle').textContent = '人流達提醒門檻';
    $('#insightBody').textContent = `目前偵測到 ${count} 人，已達 ${s.threshold} 人的自訂門檻。`;
    $('#recommendation').textContent = '建議查看現場動線是否順暢；人數增加不等於危險事件。';
  } else {
    $('#insightTitle').textContent = '目前狀態穩定';
    $('#insightBody').textContent = `目前偵測 ${count} 人，低於 ${s.threshold} 人的提醒門檻。`;
    $('#recommendation').textContent = '可持續觀察人數變化，並搭配現場情況評估空間使用需求。';
  }
  if(s.error) showFeedback(s.error, true);
  else if(s.message && mode==='stopped' && s.message.includes('完成')) showFeedback(s.message);
}
function makeChart() {
  if(!window.Chart) {$('#trendChart').insertAdjacentHTML('afterend','<p class="setting-hint">圖表需連線載入 Chart.js。</p>'); return;}
  const ctx = $('#trendChart').getContext('2d');
  const fill = ctx.createLinearGradient(0,0,0,200);fill.addColorStop(0,'rgba(82,134,250,.22)');fill.addColorStop(1,'rgba(82,134,250,0)');
  chart = new Chart(ctx,{type:'line',data:{labels:[],datasets:[{label:'平均偵測人數',data:[],borderColor:'#5188fb',backgroundColor:fill,borderWidth:2.5,pointRadius:2,pointHoverRadius:5,tension:.4,fill:true,spanGaps:false}]},options:{maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{backgroundColor:'#263a63',padding:11,displayColors:false}},scales:{x:{grid:{display:false},ticks:{color:'#a3afc1',maxTicksLimit:8,font:{size:10}},border:{display:false}},y:{beginAtZero:true,grid:{color:'#f0f3f9'},border:{display:false},ticks:{precision:0,color:'#a3afc1',font:{size:10}}}}}});
}
function renderHistory(data) {
  $('#avgCount').textContent = data.avg_count_today;
  $('#peakCount').textContent = data.peak_count_today;
  if(chart) { chart.data.labels = data.chart.map(item=>item.hour); chart.data.datasets[0].data = data.chart.map(item=>item.people); chart.update('none'); }
  const list = $('#eventsList');
  list.replaceChildren();
  if(!data.alerts.length){const el=document.createElement('div');el.className='empty-state';el.textContent='尚無提醒紀錄';list.append(el);return;}
  data.alerts.forEach(ev=>{
    const wrap=document.createElement('div');wrap.className='event';
    const icon=document.createElement('div');icon.className='event-icon';icon.textContent='⚑';
    const body=document.createElement('div');
    const title=document.createElement('div');title.className='event-title';title.textContent=`偵測 ${ev.count} 人，達提醒門檻`;
    const time=document.createElement('div');time.className='event-time';time.textContent=ev.ts.replace('T',' ') + (ev.mode==='demo'?' · 模擬數據':ev.mode==='video'?' · 影片分析':' · 攝影機');
    body.append(title,time);wrap.append(icon,body);list.append(wrap);
  });
}
async function update() {try{renderStatus(await api('/api/status'));}catch(e){showFeedback('無法連接本機後端：'+e.message,true);}}
async function updateHistory(){try{renderHistory(await api('/api/history'));}catch(e){console.error(e);}}
async function execute(action){try{const data=await action();showFeedback(data.message || '設定成功');await update();await updateHistory();}catch(e){showFeedback(e.message,true);}}
$('#startCamera').addEventListener('click',()=>execute(()=>api('/api/start',{method:'POST',body:JSON.stringify({mode:'camera',camera_index:Number($('#cameraIndex').value)})})));
$('#analyzeVideo').addEventListener('click',async()=>{
  const f=$('#videoFile').files[0];
  if(!f){showFeedback('請先選擇測試影片。',true);return;}
  if(f.size > 150*1024*1024){showFeedback('影片超過 150 MB，請選擇較短的測試影片。',true);return;}
  const button=$('#analyzeVideo'); button.disabled=true;button.textContent='上傳中…';
  try{
    const form=new FormData();form.append('file',f);
    const res=await fetch('/api/upload-video',{method:'POST',body:form});
    const data=await res.json();
    if(!res.ok||data.ok===false)throw new Error(data.message||'影片讀取失敗');
    showFeedback(data.message);await update();await updateHistory();
  }catch(err){showFeedback(err.message,true);}
  finally{button.disabled=false;button.textContent='▶ 開始分析影片';}
});
$('#startDemo').addEventListener('click',()=>execute(()=>api('/api/start',{method:'POST',body:JSON.stringify({mode:'demo'})})));
$('#stop').addEventListener('click',()=>execute(()=>api('/api/stop',{method:'POST'})));
$('#saveSettings').addEventListener('click',()=>execute(()=>api('/api/settings',{method:'POST',body:JSON.stringify({threshold:Number($('#threshold').value)})})));
makeChart();update();updateHistory();setInterval(update,2000);setInterval(updateHistory,12000);
