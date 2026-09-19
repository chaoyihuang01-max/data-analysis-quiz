from pathlib import Path
import json, re

path = Path("index.html")
s = path.read_text("utf-8")
if "data2027/part-040.js" in s and "bankSelect" in s and "QUESTIONS.push(...(window.NEW_2027||[]))" in s:
    print("2027 bank already enabled")
    raise SystemExit(0)

s = s.replace("资料分析拔高刷题系统 <small>192题 · 12章</small>",
              "资料分析拔高刷题系统 <small>350题 · 2026+2027 · 22章</small>")

needle = '<select id="mobileChapter" class="select mobileChapters"></select>'
repl = '''<select id="bankSelect" class="select" title="题库版本">
            <option value="all">全部题库（2026+2027）</option>
            <option value="2027">2027 夸夸刷</option>
            <option value="2026">2026 专项拔高</option>
          </select>
          <select id="mobileChapter" class="select mobileChapters"></select>'''
if needle not in s:
    raise RuntimeError("mobileChapter anchor not found")
s = s.replace(needle, repl, 1)

script_idx = s.index("<script>\nconst QUESTIONS =")
parts = "\n".join(f'<script src="data2027/part-{i:03d}.js"></script>' for i in range(1, 41)) + "\n"
s = s[:script_idx] + parts + s[script_idx:]

q_marker = "const QUESTIONS = "
qstart = s.index(q_marker) + len(q_marker)
in_str = False
esc = False
depth = 0
end = None
for i, ch in enumerate(s[qstart:], start=qstart):
    if in_str:
        if esc:
            esc = False
        elif ch == "\\":
            esc = True
        elif ch == '"':
            in_str = False
    else:
        if ch == '"':
            in_str = True
        elif ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
if end is None or s[end] != ";":
    raise RuntimeError("QUESTIONS array end not found")

insert = '''
QUESTIONS.forEach(q=>{if(!q.bank)q.bank="2026";if(!q.label)q.label=`例${q.example}`;});
QUESTIONS.push(...(window.NEW_2027||[]));'''
s = s[:end+1] + insert + s[end+1:]

m = re.search(r"const CHAPTER_TITLES = (\\{.*?\\});", s, re.S)
if not m:
    raise RuntimeError("CHAPTER_TITLES not found")
titles = json.loads(m.group(1))
titles.update({
    "101": "2027 第一章 基期",
    "102": "2027 第二章 现期",
    "103": "2027 第三章 增长量",
    "104": "2027 第四章 一般增长率",
    "105": "2027 第五章 间隔增长率、年均增长率",
    "106": "2027 第六章 乘积增长率、混合增长率",
    "107": "2027 第七章 比重",
    "108": "2027 第八章 平均数",
    "109": "2027 第九章 倍数",
    "110": "2027 第十章 切入点与易错点"
})
s = s[:m.start()] + "const CHAPTER_TITLES = " + json.dumps(titles, ensure_ascii=False) + ";" + s[m.end():]

s = s.replace('let activeChapter = "all";', 'let activeBank = "all";\nlet activeChapter = "all";', 1)

start = s.index("function buildChapters(){")
endf = s.index("function chapterButton", start)
new_build = '''function bankQuestions(){return QUESTIONS.filter(q=>activeBank==="all"||q.bank===activeBank)}
function buildChapters(){
  const bqs=bankQuestions();
  const counts={}; bqs.forEach(q=>counts[q.chapter]=(counts[q.chapter]||0)+1);
  const list=document.getElementById("chapterList");
  list.innerHTML="";
  const allLabel=activeBank==="all"?"全部题目":`${activeBank} 全部题目`;
  list.appendChild(chapterButton("all",allLabel,bqs.length));
  const visible=Object.keys(CHAPTER_TITLES).sort((a,b)=>+a-+b).filter(ch=>(counts[ch]||0)>0);
  visible.forEach(ch=>list.appendChild(chapterButton(String(ch),CHAPTER_TITLES[ch],counts[ch]||0)));
  const sel=document.getElementById("mobileChapter");
  sel.innerHTML='<option value="all">全部章节</option>'+visible.map(ch=>`<option value="${ch}">${CHAPTER_TITLES[ch]}</option>`).join("");
  if(activeChapter!=="all"&&!visible.includes(String(activeChapter))) activeChapter="all";
  sel.value=String(activeChapter);
}
'''
s = s[:start] + new_build + s[endf:]

s = s.replace(
    'let arr=QUESTIONS.filter(q=>activeChapter==="all"||String(q.chapter)===String(activeChapter));',
    'let arr=QUESTIONS.filter(q=>(activeBank==="all"||q.bank===activeBank)&&(activeChapter==="all"||String(q.chapter)===String(activeChapter)));',
    1
)
s = s.replace(
    'document.getElementById("qTitle").textContent=`${q.topic} · 例${q.example}`;',
    'document.getElementById("qTitle").textContent=`${q.topic} · ${q.label||("例"+q.example)}`;',
    1
)
s = s.replace(
    'document.getElementById("qMeta").textContent=`第 ${currentIndex+1} / ${currentList.length} 题 · 来源${q.source}`;',
    'document.getElementById("qMeta").textContent=`第 ${currentIndex+1} / ${currentList.length} 题 · ${q.bank||"2026"}题库 · 来源${q.source}`;',
    1
)
s = s.replace(
    'const wrong=QUESTIONS.filter(q=>answerFor(q)&&!isCorrect(q));',
    'const wrong=QUESTIONS.filter(q=>(activeBank==="all"||q.bank===activeBank)&&answerFor(q)&&!isCorrect(q));',
    1
)
s = s.replace(
    'const base=QUESTIONS.filter(q=>activeChapter==="all"||String(q.chapter)===String(activeChapter));',
    'const base=QUESTIONS.filter(q=>(activeBank==="all"||q.bank===activeBank)&&(activeChapter==="all"||String(q.chapter)===String(activeChapter)));',
    1
)
s = s.replace(
    '收藏 ${QUESTIONS.filter(q=>isFavorite(q)).length} 题`;',
    '收藏 ${QUESTIONS.filter(q=>(activeBank==="all"||q.bank===activeBank)&&isFavorite(q)).length} 题`;',
    1
)

old_loop = '''  for(let ch=1;ch<=12;ch++){
    const qs=QUESTIONS.filter(q=>q.chapter===ch), d=qs.filter(q=>answerFor(q)), c=d.filter(q=>isCorrect(q));'''
new_loop = '''  for(const chKey of Object.keys(CHAPTER_TITLES).sort((a,b)=>+a-+b)){
    const ch=Number(chKey);
    const qs=QUESTIONS.filter(q=>Number(q.chapter)===ch), d=qs.filter(q=>answerFor(q)), c=d.filter(q=>isCorrect(q));'''
if old_loop not in s:
    raise RuntimeError("dashboard chapter loop not found")
s = s.replace(old_loop, new_loop, 1)
s = s.replace('${q.topic} · 例${q.example}</td>', '${q.topic} · ${q.label||(`例${q.example}`)}</td>')

old_go = '''function goQuestion(id){
  showQuiz(); activeChapter="all"; filter="all"; orderMode="sequence";
  document.getElementById("mobileChapter").value="all"; document.getElementById("orderMode").value="sequence";'''
new_go = '''function goQuestion(id){
  const target=QUESTIONS.find(q=>q.id===id);
  showQuiz(); activeBank=target?.bank||"all"; activeChapter="all"; filter="all"; orderMode="sequence";
  document.getElementById("bankSelect").value=activeBank; buildChapters();
  document.getElementById("mobileChapter").value="all"; document.getElementById("orderMode").value="sequence";'''
if old_go not in s:
    raise RuntimeError("goQuestion anchor not found")
s = s.replace(old_go, new_go, 1)

mobile_evt = 'document.getElementById("mobileChapter").onchange=e=>{activeChapter=e.target.value;refreshChapterButtons();rebuildList(true)};'
bank_evt = 'document.getElementById("bankSelect").onchange=e=>{activeBank=e.target.value;activeChapter="all";buildChapters();refreshChapterButtons();rebuildList(true)};\n'
if mobile_evt not in s:
    raise RuntimeError("mobile chapter event not found")
s = s.replace(mobile_evt, bank_evt + mobile_evt, 1)
s = s.replace("buildChapters();\nrebuildList(false);", 'document.getElementById("bankSelect").value=activeBank;\nbuildChapters();\nrebuildList(false);', 1)
s = s.replace("资料分析拔高刷题系统 - 高清版", "资料分析刷题系统 - 2026+2027 高清版")
s = s.replace("基于你当前浏览器中保存的作答记录实时生成。", "覆盖 2026 与 2027 两套题库，基于当前浏览器保存的作答记录实时生成。")

path.write_text(s, "utf-8")
print("Enabled 2027 bank; index bytes:", path.stat().st_size)
