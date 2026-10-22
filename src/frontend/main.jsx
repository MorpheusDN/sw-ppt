import React,{useCallback,useEffect,useRef,useState} from 'react';
import {createRoot} from 'react-dom/client';
import * as echarts from 'echarts/core';
import {GraphChart} from 'echarts/charts';
import {TooltipComponent} from 'echarts/components';
import {SVGRenderer} from 'echarts/renderers';
echarts.use([GraphChart,TooltipComponent,SVGRenderer]);

const states={EFFECTIVE:'当前有效',HISTORICAL:'历史事实',FUTURE:'晚于查询时间',CONFLICT:'存在冲突',UNCERTAIN_TIME:'时间不确定',UNCERTAIN_PLAN:'尚属计划',RETRIEVED_UNRESOLVED:'尚未解析'};
const examples={current:['conv-26',"What is Caroline's current adoption status?",''],past:['conv-26',"What is Caroline's adoption status?",'2023-06-01T23:59:59'],hobbies:['conv-42','What hobbies does Nate enjoy?',''],conflict:['conv-30','Does Gina still work at Door Dash?',''],unknown:['conv-26',"What is Caroline's salary?",'']};
async function api(url,data){
 const response=await fetch(url,data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
 const payload=await response.json();if(!response.ok)throw new Error(payload.error||'请求失败');return payload;
}
function download(name,data){const blob=new Blob([JSON.stringify(data,null,2)],{type:'application/json;charset=utf-8'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),2000);}

function RelationGraph({result,onSelect}){
 const host=useRef(null);
 useEffect(()=>{
  if(!result?.candidates.length||!host.current)return;
  const chart=echarts.init(host.current,null,{renderer:'svg'});
  const data=result.candidates.slice().sort((a,b)=>(a.event_time||'').localeCompare(b.event_time||'')||a.source.turns[0].localeCompare(b.source.turns[0]));
  const n=data.length;
  chart.setOption({animation:false,tooltip:{trigger:'item',renderMode:'richText',formatter:p=>p.dataType==='edge'?p.data.label:p.data.name},
    series:[{type:'graph',layout:'none',roam:true,draggable:true,
      data:data.map((m,i)=>({id:m.memory_id,name:m.source.turns.join(', ')+'\n'+m.attribute+'\n'+(states[result.decisions[m.memory_id]]||'未解析'),
        x:90+(i%5)*190,y:80+Math.floor(i/5)*150,symbol:'roundRect',symbolSize:[150,80],
        itemStyle:{color:result.decisions[m.memory_id]==='EFFECTIVE'?'#d7efed':'#edf2f5',borderColor:result.decisions[m.memory_id]==='CONFLICT'?'#bb5b42':'#6e9eaa',borderWidth:1.5}})),
      links:result.relations.map(p=>({source:p.from_id,target:p.to_id,label:p.label,
        lineStyle:{color:p.label==='CONFLICT'?'#bb5b42':'#168b96',curveness:.18},
        edgeSymbol:['none','arrow']})),
      label:{show:true,color:'#193342',fontFamily:'Microsoft YaHei',fontSize:11,lineHeight:17,width:140,overflow:'truncate'},
      edgeLabel:{show:true,formatter:p=>p.data.label,fontSize:10,color:'#27616d'},
      lineStyle:{width:1.8},emphasis:{focus:'adjacency'}}]});
  chart.on('click',p=>{if(p.dataType==='node')onSelect(p.data.id);});
  const observer=new ResizeObserver(()=>chart.resize());observer.observe(host.current);
  return ()=>{observer.disconnect();chart.dispose();};
 },[result,onSelect]);
 return result?.candidates.length?<div id="graph" ref={host} role="img" aria-label="候选记忆之间的关系图，详细关系可在下方表格查阅" style={{height:260,width:'100%',minWidth:0}}/>:<p id="graph" className="muted">没有检索到相关记忆。</p>;
}

function App(){
 const [conversations,setConversations]=useState([]),[cid,setCid]=useState(''),[memories,setMemories]=useState([]);
 const [question,setQuestion]=useState("What is Caroline's current adoption status?"),[asOf,setAsOf]=useState(''),[method,setMethod]=useState('dynamic_lexical'),[k,setK]=useState(10),[openDomain,setOpenDomain]=useState(false);
 const [result,setResult]=useState(null),[selected,setSelected]=useState(null),[filter,setFilter]=useState(''),[health,setHealth]=useState(null);
 const [message,setMessage]=useState('正在加载数据…'),[error,setError]=useState(false),[busy,setBusy]=useState(false);
 const file=useRef(null),generation=useRef(0);
 const tell=(text,bad=false)=>{setMessage(text);setError(bad);};
 const showDetail=useCallback(id=>setSelected(id),[]);
 const load=useCallback(async id=>{
  const ticket=++generation.current;setResult(null);setSelected(null);
  const data=await api('/api/memories?conversation_id='+encodeURIComponent(id));
  if(ticket===generation.current)setMemories(data.memories);
 },[]);
 const refresh=useCallback(async()=>{
  const [data,h]=await Promise.all([api('/api/conversations'),api('/api/health')]);
  setConversations(data.conversations);setHealth(h);
  const id=data.conversations[0]?.conversation_id||'';setCid(id);if(id)await load(id);
 },[load]);
 useEffect(()=>{refresh().then(()=>tell('数据已加载。')).catch(e=>tell(e.message,true));},[refresh]);
 async function choose(id){setCid(id);try{await load(id);}catch(e){tell(e.message,true);}}
 async function example(name){const [id,q,t]=examples[name];if(!conversations.some(c=>c.conversation_id===id))return tell('该示例需要导入真实 LoCoMo 对话。',true);setQuestion(q);setAsOf(t);setOpenDomain(false);await choose(id);}
 async function ask(e){
  e.preventDefault();setBusy(true);tell('正在检索与解析…');
  const ticket=generation.current;
  try{
   const payload={conversation_id:cid,question,k:Number(k),method,open_domain:openDomain};if(asOf)payload.as_of=asOf;
   const response=await api('/api/query',payload);
   if(ticket!==generation.current)return;
   setResult(response);setSelected(response.candidates[0]?.memory_id||null);
   tell(response.answer_status==='context_only'?'完整对话上下文已准备，可保存查询记录查看。':'查询完成。点击记忆可查看来源。');
  }catch(err){tell(err.message,true);}finally{setBusy(false);}
 }
 async function importData(){try{const f=file.current.files[0];if(!f)throw new Error('请先选择 JSON 文件。');if(f.size>20*1024*1024)throw new Error('文件超过 20 MiB');const response=await api('/api/import',{data:JSON.parse(await f.text())});await refresh();tell(`已导入 ${response.imported_conversations} 段对话，构建 ${response.memories} 条记忆。`);}catch(e){tell(e.message,true);}}
 const detail=memories.find(m=>m.memory_id===selected),shown=memories.filter(m=>JSON.stringify(m).toLowerCase().includes(filter.toLowerCase()));
 const source=id=>memories.find(m=>m.memory_id===id)?.source.turns.join(', ')||id;
 return <><header><div><small>RISC-V · SOFTWARE REQUIREMENTS ENGINEERING</small><h1>动态记忆工作台</h1><p>查看历史事实，理解状态变化，追溯每一条证据。</p></div><span id="datasetBadge">{conversations.length&&conversations.every(c=>c.conversation_id.startsWith('synthetic-'))?'人工构造演示数据':conversations.length?'已导入本地对话':'正在加载数据'}</span></header>
 <main><section aria-labelledby="queryTitle"><h2 id="queryTitle">查询与时间条件</h2>
 <form id="queryForm" onSubmit={ask}><div className="controls">
 <label>对话<select id="conversation" value={cid} onChange={e=>choose(e.target.value)} disabled={busy}>{conversations.map(c=><option key={c.conversation_id} value={c.conversation_id}>{c.conversation_id} · {c.turns} 轮</option>)}</select></label>
 <label>方法<select id="method" value={method} onChange={e=>setMethod(e.target.value)}><option value="dynamic_lexical">动态解析 · 词法候选</option><option value="lexical">词法检索 · 无动态解析</option><option value="vector" disabled={!health?.vector_available}>Vector RAG · MiniLM</option><option value="dynamic_vector" disabled={!health?.vector_available}>MiniLM + 动态解析</option><option value="hybrid" disabled={!health?.vector_available}>混合检索 + 动态解析</option><option value="full_text">Full Text · 全历史窗口问答</option></select></label>
 <label>候选数量 K<input id="topK" type="number" min="1" max="100" value={k} onChange={e=>setK(e.target.value)}/></label>
 <label>查询时间 可选<input id="asOf" type="datetime-local" step="1" value={asOf} onChange={e=>setAsOf(e.target.value)}/></label></div>
 <div className="question"><input id="question" aria-label="英文问题" required value={question} onChange={e=>setQuestion(e.target.value)}/><button id="ask" type="submit" disabled={busy||!cid}>检索并解析</button></div><label><input id="openDomain" type="checkbox" checked={openDomain} onChange={e=>setOpenDomain(e.target.checked)}/> 通用问答：检索全部属性与人物，历史时间请手动指定</label></form>
 <div className="examples">{[['current','Caroline 当前状态'],['past','Caroline 历史状态'],['hobbies','Nate 兴趣'],['conflict','Gina 工作证据'],['unknown','证据不足']].map(([key,label])=><button key={key} type="button" disabled={busy} data-example={key} onClick={()=>example(key)}>{label}</button>)}</div>
 <div id="message" role="status" aria-live="polite" className={error?'error':''}>{message}</div></section>
 {result&&<section className="answer" id="answerArea"><h2>回答</h2><p id="answerText">{result.answer}</p><div id="answerMeta">状态 {result.answer_status}　参照时间 {result.as_of||'未知'}<br/>{result.time_reference==='conversation_end'?'默认以所选对话结束时间为参照':'使用显式查询时间'}　候选 {result.candidates.length} 条　有效 {result.effective_ids.length} 条</div><p id="citationText">答案来源 {(result.answer_source_turns||result.candidates.filter(m=>result.evidence_ids.includes(m.memory_id)).flatMap(m=>m.source.turns)).join(', ')}</p></section>}
 <div className="workspace"><section><div className="sectionhead"><h2>结构化记忆</h2><span id="memoryCount">{shown.length} / {memories.length} 条</span></div><input id="filter" aria-label="筛选记忆" placeholder="筛选人物、属性或原文" value={filter} onChange={e=>setFilter(e.target.value)}/><div id="memories">{shown.map(m=><button key={m.memory_id} type="button" className={'memory'+(selected===m.memory_id?' selected':'')} onClick={()=>showDetail(m.memory_id)}><small>{m.entity} · {m.attribute} · {m.source.turns.join(', ')}</small><strong>{m.content}</strong><small>{m.event_time||'时间未知'}</small>{result?.decisions[m.memory_id]&&<span className="state">{states[result.decisions[m.memory_id]]}</span>}</button>)}</div></section>
 <section><h2>来源与结构</h2><p className="muted">选择一条记忆，查看完整原始轮次与时间依据。</p><div id="detail">{detail&&<><dl>{[['人物',detail.entity],['属性',detail.attribute],['值',detail.value],['会话时间',detail.session_time],['事件时间',detail.event_time],['时间依据',detail.time_basis],['来源轮次',detail.source.turns.join(', ')],['本次有效性',result?states[result.decisions[detail.memory_id]]||'未进入候选':'尚未查询']].map(([label,value])=><React.Fragment key={label}><dt>{label}</dt><dd>{value??'未知'}</dd></React.Fragment>)}</dl><h3>原始轮次</h3><blockquote>{detail.source.text}</blockquote><details><summary>完整 JSON</summary><pre>{JSON.stringify(detail,null,2)}</pre></details></>}</div></section></div>
 {result&&<section id="relationsArea"><h2>关系与有效性</h2><p className="muted">关系仅对本次问题及时间条件生效。完整记忆库始终保留历史记录。可缩放、拖动或点击图中节点。</p><RelationGraph result={result} onSelect={showDetail}/><div className="tablewrap"><table><thead><tr><th>原证据</th><th>关系</th><th>后续证据</th><th>依据</th></tr></thead><tbody id="relations">{result.relations.length?result.relations.map((p,i)=><tr key={i}><td>{source(p.from_id)}</td><td>{p.label}</td><td>{source(p.to_id)}</td><td>{p.reason}</td></tr>):<tr><td colSpan="4">本次没有可判定的记忆关系</td></tr>}</tbody></table></div></section>}
 <section><h2>数据管理</h2><p>默认数据为人工构造的回归样例。可导入 LoCoMo 原始 JSON 或本项目的标准对话格式。</p><div className="actions"><label className="filelabel">选择 JSON<input id="importFile" ref={file} type="file" accept=".json,application/json"/></label><button id="importButton" onClick={importData}>导入并重建记忆</button><button id="exportButton" onClick={()=>api('/api/export').then(x=>download('memory-export.json',x)).catch(e=>tell(e.message,true))}>导出 Memory JSON</button><button id="saveResult" disabled={!result} onClick={()=>download(result.query_id+'.json',result)}>保存本次查询记录</button></div><p className="muted">导入成功后保存为 data/imported.json。重启时需用 --data data/imported.json 指定。</p></section>
 </main><footer>RISC-V · React + ECharts · 英文文本对话</footer></>;
}
createRoot(document.getElementById('root')).render(<App/>);
