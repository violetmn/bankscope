const $ = id => document.getElementById(id);
let documents = [], capabilities = {}, busy = false;
function el(tag, text, className) { const node = document.createElement(tag); if(text != null) node.textContent = text; if(className) node.className = className; return node; }
function setStatus(message, error = false) { $('status').textContent = message; $('status').className = error ? 'error' : ''; }
function years() {
  const values = [...new Set(documents.filter(d => !$('company').value || d.company === $('company').value).map(d=>d.year))].sort((a,b)=>b-a);
  $('year').replaceChildren(new Option('All years', ''), ...values.map(y => new Option(y,y)));
  if(values.length) $('year').value=String(values[0]);
}
async function initialize() {
  try {
    const responses = await Promise.all([fetch('/documents'),fetch('/capabilities')]);
    if(responses.some(r=>!r.ok)) throw Error('Could not load the report library. Refresh to try again.');
    [documents,capabilities] = await Promise.all(responses.map(r=>r.json()));
    $('doc-count').textContent=documents.length;
    const companies=[...new Set(documents.map(d=>d.company))];
    $('company').replaceChildren(new Option('All companies',''), ...companies.map(c=>new Option(c,c)));
    if(companies.length) $('company').value=companies[0];
    years(); $('library').replaceChildren();
    for(const doc of documents) {
      const card=el('article',null,'document-card');
      card.append(el('span','▤','doc-icon'),el('h3',doc.company),el('p',`${doc.year} · Annual report`),el('p',`${doc.pages} pages · Source indexed`),el('span','READY TO SEARCH','doc-tag'));
      card.append(el('p',doc.structured_table_ready?'Checked deposit table available':'Text search available · table extraction not validated','table-caption'));
      const use=el('button',`Use ${doc.year} report`,'select-report');use.type='button';use.addEventListener('click',()=>{$('company').value=doc.company;years();$('year').value=String(doc.year);$('question').focus();setStatus(`Research scoped to ${doc.company}, report ${doc.year}.`);});card.append(use);
      $('library').append(card);
    }
    if(!documents.length) { $('library').append(el('p','No reports have been added yet.','muted')); $('submit').disabled=true; setStatus('Add a report with the ingestion command before searching.'); }
    $('search-badge').textContent=capabilities.default_strategy==='financial'?'● Table-aware + semantic search':capabilities.default_strategy==='rerank'?'● Semantic search + reranking':capabilities.semantic_ready?'● Semantic search ready':'● Keyword search ready';
    $('generation-option').hidden=!capabilities.generation_enabled;
  } catch(error) { setStatus(error.message,true); $('submit').disabled=true; $('search-badge').textContent='Search unavailable'; }
}
function renderSources(hits) {
  $('source-list').replaceChildren();
  hits.forEach((hit,index)=>{
    const card=el('article',null,'source-card'), heading=el('div',null,'source-heading');
    heading.append(el('h3',`${String(index+1).padStart(2,'0')} / ${hit.company} · ${hit.year}`));
    if(hit.source_url && (/^https?:\/\//.test(hit.source_url)||hit.source_url.startsWith('/reports/'))) {
      const link=el('a',`Open PDF page ${hit.page} ↗`); link.href=hit.source_url;link.target='_blank';link.rel='noopener noreferrer'; heading.append(link);
    }
    card.append(heading,el('div',hit.citation,'source-context'));
    if(hit.source_kind==='financial_table_excerpt') card.append(el('p','Source table excerpt · verify year, units and row labels.','table-caption'));
    const text=hit.text, preview=text.length>550?text.slice(0,550)+'…':text;
    card.append(el('p',preview,'source-text'));
    if(text.length>550) { const details=el('details'),summary=el('summary','Read full passage'); details.append(summary,el('p',text,'source-text'));card.append(details); }
    $('source-list').append(card);
  });
}
function renderTableResult(analysis) {
  const table=analysis.table, card=el('article',null,'table-result');
  card.append(el('div','STRUCTURED SOURCE · NO AI CALL','eyebrow'),el('h3',table.title),el('p',analysis.answer,'table-answer'));
  card.append(el('p',`${table.company} · Report ${table.report_year} · PDF page ${table.pdf_page}. All values in ${table.unit} of report dollars ($).`,'table-caption'));
  const scroll=el('div',null,'table-scroll'), grid=el('table',null,'financial-table'), head=el('thead'), header=el('tr');
  const label=el('th',table.category_label||'Deposit category');label.scope='col';header.append(label);
  table.years.forEach(year=>{const h=el('th',String(year));h.scope='col';header.append(h);});head.append(header);grid.append(head);
  const body=el('tbody');
  const format=value=>Number(value).toLocaleString('en-US',{maximumFractionDigits:6});
  table.rows.forEach(row=>{const tr=el('tr'), h=el('th',row.label);h.scope='row';tr.append(h);table.years.forEach(year=>tr.append(el('td',format(row.values[String(year)]))));body.append(tr);});
  grid.append(body);const foot=el('tfoot'), total=el('tr');total.append(el('th',table.total_label||'Total customer deposits'));
  table.years.forEach(year=>total.append(el('td',format(table.totals[String(year)]))));foot.append(total);grid.append(foot);scroll.append(grid);card.append(scroll);
  if(Object.values(table.reconciliation).every(check=>check.matches)) card.append(el('p','✓ Every extracted category sums exactly to the reported total in each year.','reconciled'));
  if(table.category_basis==='business_segment') card.append(el('p','Period-end balances by business segment. Average balances and deposit product types are different measures.','table-caption'));
  if(analysis.calculation) {const c=analysis.calculation;card.append(el('p',`Python calculation: (${c.to_value} − ${c.from_value}) ÷ ${c.from_value} × 100. Percentage rounded to two decimal places.`,'calculation-note'));}
  if(table.source_url?.startsWith('/reports/')) {const link=el('a',`Inspect the original table · PDF page ${table.pdf_page} ↗`);link.href=table.source_url;link.target='_blank';link.rel='noopener noreferrer';card.append(link);}
  card.append(el('p','Checks apply to this extracted table, not every table in the report.','table-caption'));
  $('source-list').replaceChildren(card);
}
async function search(event) {
  event.preventDefault(); if(busy || !$('question-form').reportValidity()) return;
  busy=true; $('submit').disabled=true; $('submit').textContent='Searching…';
  $('results').hidden=true; $('welcome').hidden=true; $('answer').hidden=true;
  setStatus('Finding relevant passages in the report…');
  const started=performance.now();
  try {
    const response=await fetch('/query',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:$('question').value.trim(),company:$('company').value||null,year:$('year').value?Number($('year').value):null,k:5,generate_answer:$('generate').checked})});
    const data=await response.json();
    if(!response.ok) throw Error(typeof data.detail==='string'?data.detail:'The search could not complete. Please try again.');
    if(data.table_analysis) {
      $('results').hidden=false;$('result-title').textContent='Source table & checked calculations';
      $('result-meta').textContent=`Local calculation · ${((performance.now()-started)/1000).toFixed(1)}s`;
      renderTableResult(data.table_analysis);
      setStatus('This result uses the extracted table and Python arithmetic. No paid AI request was made.');
      return;
    }
    $('results').hidden=false; $('result-title').textContent=data.sources.length?'Passages to review':'No matching passages';
    $('result-meta').textContent=`${data.sources.length} passages · ${((performance.now()-started)/1000).toFixed(1)}s`;
    renderSources(data.sources);
    setStatus(data.sources.length?'These are source excerpts, not a verified answer. Open a PDF page to check the full context.':'Try a different question, company, or year.');
    if(data.generation) {
      const failed = ['error','citation_check_failed','incomplete_response','abstained','no_evidence'].includes(data.generation.status);
      $('answer').hidden=false; $('answer').replaceChildren(el('h3',failed?'AI answer unavailable · source search still works':'AI answer · verify against sources'),el('div',data.generation.answer));
      if(failed) setStatus('The report search worked, but the AI request failed. See the explanation below.',true);
      if(data.generation.warnings?.length) {
        const warning = el('div',null,'answer-warning');
        warning.append(el('h3','Numerical review needed'));
        data.generation.warnings.forEach(message=>warning.append(el('p',message)));
        $('answer').append(warning);
      }
      if(data.generation.sources) $('answer').append(el('p',Object.entries(data.generation.sources).map(([id,citation])=>`${id}: ${citation}`).join('\n'),'source-context'));
    }
  } catch(error) { setStatus(error.message,true); }
  finally {busy=false;$('submit').disabled=false;$('submit').replaceChildren(document.createTextNode('Find evidence '),el('span','↗'));}
}
$('company').addEventListener('change',years);
$('question-form').addEventListener('submit',search);
document.querySelectorAll('[data-question]').forEach(button=>button.addEventListener('click',()=>{if(busy)return;$('question').value=button.dataset.question;$('question').focus();$('question-form').requestSubmit();}));
initialize();
