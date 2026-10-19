"""Development retrieval variant: question-derived scope and financial query expansion.

No benchmark IDs, reference answers, financial values or evidence pages are used.
"""
import re
import numpy as np
from bankscope.semantic import MODEL,encoder,reranker,ready,reranker_ready,distinct_pages

ALIASES={'american express':('american express','amex'),
         'jpmorgan':('jpmorgan chase','jpmorgan','j.p. morgan','jpm')}


def aliases(company):
    normalized=company.casefold()
    for key,values in ALIASES.items():
        if key in normalized:return values
    return (normalized,)


def mentioned(question,company):
    return any(re.search(r'(?<!\w)'+re.escape(a)+r"(?:['’]s)?(?!\w)",question,re.I) for a in aliases(company))


def resolve_scope(question,documents,company=None,year=None,doc_id=None):
    if doc_id or company is not None:return company,year,doc_id
    matched={d['company'] for d in documents if mentioned(question,d['company'])}
    if len(matched)!=1:return company,year,doc_id
    company=next(iter(matched))
    explicit_years={int(x) for x in re.findall(r'(?<!\d)(20\d{2})(?!\d)',question)}
    if year is None and len(explicit_years)==1:year=next(iter(explicit_years))
    quarter=re.search(r'\bQ([1-4])\b',question,re.I)
    if quarter and year is not None:
        docs=[d for d in documents if d['company']==company and d['year']==year
              and re.search(r'_'+str(year)+'Q'+quarter[1]+r'_',d['id'],re.I)]
        if len(docs)==1:doc_id=docs[0]['id']
    return company,year,doc_id


def queries(question,company=None):
    query=question
    if company:
        for alias in sorted(aliases(company),key=len,reverse=True):
            query=re.sub(r'(?<!\w)'+re.escape(alias)+r"(?:['’]s)?(?!\w)",' ',query,flags=re.I)
    # Keep semantic comparator words but remove generic instruction boilerplate.
    primary=re.split(r'\?\s*If\b',query,flags=re.I)[0].strip()
    primary=re.sub(r'\bFY\s*(20\d{2})\b',r'\1',primary,flags=re.I)
    primary=' '.join(primary.split()).strip(' ?.,')
    variants=[primary or question]
    text=question.casefold()
    if 'segment' in text and ('revenue' in text or 'income' in text):
        variants.append('segment results managed basis '+('net income' if 'net income' in text else 'net revenue'))
    elif 'tax rate' in text:
        variants.append('effective tax rate income tax provision pretax income')
    elif 'margin' in text:
        variants.extend(['consolidated income statement revenues net interest income expenses',
                         'business overview financial institution financial services'])
    elif re.search(r'\b(?:retain|retention|attrition)\b',text):
        variants.append('card member retention attrition existing customers business performance')
    elif ('shareholder' in text or 'per share' in text) and ('liquidat' in text or 'bankrupt' in text):
        variants.append('tangible book value per share stockholders equity shares outstanding')
    return list(dict.fromkeys(variants))[:3]


def search(store,question,k,company=None,year=None,doc_id=None):
    if not ready(store) or not reranker_ready():
        raise ValueError('Focused retrieval requires prepared embeddings and reranker')
    company,year,doc_id=resolve_scope(question,store.documents(),company,year,doc_id)
    conditions,args=['e.model=?'],[MODEL]
    for field,value in [('company',company),('year',year),('id',doc_id)]:
        if value is not None:conditions.append(f'd.{field}=?');args.append(value)
    rows=store.db.execute('''SELECT p.text,p.doc_id,p.page,p.chunk_id,d.company,d.year,d.url,e.vector
      FROM passages p JOIN documents d ON p.doc_id=d.id JOIN embeddings e ON p.chunk_id=e.chunk_id
      WHERE '''+' AND '.join(conditions)+' ORDER BY p.chunk_id',args).fetchall()
    if not rows:return []
    if company is None and doc_id:company=rows[0]['company']
    variants=queries(question,company)
    matrix=np.stack([np.frombuffer(r['vector'],dtype=np.float32) for r in rows])
    candidates={}
    for query in variants:
        v=np.asarray(next(encoder().query_embed(query)),dtype=np.float32);v/=max(float(np.linalg.norm(v)),1e-12)
        order=np.argsort(-(matrix@v),kind='stable')
        dense=[];pages=set()
        for idx in order:
            row=dict(rows[int(idx)]);page=(row['doc_id'],int(row['page']))
            if page in pages:continue
            pages.add(page);row.pop('vector');row['page']=page[1]
            row['citation']=f"[{row['doc_id']}, PDF page {row['page']}]"
            row['source_url']=row['url'].split('#')[0]+f"#page={row['page']}" if row['url'] else ''
            dense.append(row)
            if len(dense)==20:break
        for hit in dense+store.search(query,20,company,year,doc_id,strategy='bm25'):
            candidates.setdefault(hit['chunk_id'],hit)
    # Preserve per-query diversity while bounding inference cost.
    candidates=list(candidates.values())[:100]
    scores=list(reranker().rerank(variants[0],[h['text'] for h in candidates],batch_size=8))
    ranked=sorted(({**h,'rerank_score':float(score)} for h,score in zip(candidates,scores,strict=True)),
                  key=lambda h:(-h['rerank_score'],h['chunk_id']))
    return distinct_pages(ranked,k)
