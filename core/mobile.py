"""Mobile companion app generator.

Renders the entire tracker (timesheet, dashboard, invoice, log form) into ONE
self-contained HTML file with the data embedded as JSON. The desktop app
regenerates it after every save into the OneDrive mirror folder (plus any
extra copy dirs from config), so opening it on the phone via the OneDrive app
always shows current data.

Phone -> PC entries: the Log tab exports a small JSON file which the user
shares/saves into <mirror>/inbox/ on OneDrive; the desktop app imports it
(see core/inbox.py).

No external JS/CSS - the file must work offline from a content:// URI.
"""

import datetime as dt
import json
import os
import re

from . import config as cfgmod

MOBILE_FILENAME = "Work Hours Mobile.html"
INBOX_DIRNAME = "inbox"


def inbox_label(cfg):
    """Show an inbox label without exposing a local OS username or tenant."""
    mirror = cfg.get("onedrive_mirror_dir") or ""
    parts = [p for p in re.split(r"[\\/]+", mirror) if p]
    for i, p in enumerate(parts):
        if p.lower().startswith("onedrive"):
            parts = ["OneDrive", *parts[i + 1:]]
            break
    else:
        parts = ["sync folder"] if mirror else ["your chosen sync folder"]
    return " › ".join(parts + [INBOX_DIRNAME])


def build_payload(entries, cfg):
    """JSON-safe snapshot of everything the mobile app needs."""
    include_details = bool(cfg.get("mobile_include_invoice_details", False))
    return {
        "generated": dt.datetime.now().strftime("%a %d %b %Y, %H:%M"),
        "entries": [
            {
                "d": e.date.isoformat(),
                "s": e.start.strftime("%H:%M") if e.start else None,
                "f": e.finish.strftime("%H:%M") if e.finish else None,
                "b": e.break_min,
                "o": e.overtime or 0,
                "t": e.type,
                "su": e.summary or "",
            }
            for e in sorted(entries, key=lambda e: e.date)
        ],
        "rates": [
            {"d": d.isoformat(), "r": r} for d, r in cfgmod.sorted_rates(cfg)
        ],
        "personal": cfg.get("personal", {}) if include_details else {},
        "bill_to": cfg.get("bill_to", {}) if include_details else {},
        "payment": cfg.get("payment", {}) if include_details else {},
        "includesInvoiceDetails": include_details,
        "invoice": {
            "next_number": cfg.get("invoice", {}).get("next_number", 1) if include_details else 1,
            "self_note": cfg.get("invoice", {}).get("self_employed_note", "") if include_details else "",
            "thanks": cfg.get("invoice", {}).get("thanks_template", "") if include_details else "",
        },
        "types": ["Office", "Office (no break)", "Office + home eve",
                  "Weekend (home)", "Work from home"],
        "defaults": {key: cfg.get("defaults", {}).get(key, "")
                     for key in ("start", "finish", "break_min", "type")},
        "inboxLabel": inbox_label(cfg),
    }


def render_html(entries, cfg):
    payload = json.dumps(build_payload(entries, cfg), ensure_ascii=False)
    payload = payload.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return _TEMPLATE.replace("__WH_DATA__", payload)


def export_all(entries, cfg):
    """Write the mobile app to the mirror dir + extra copy dirs, and make sure
    the inbox folder exists. Never raises - returns list of (path, error)."""
    results = []
    if not cfg.get("mobile_export_enabled", False):
        return results
    html = None
    targets = []
    mirror = cfg.get("onedrive_mirror_dir")
    if mirror:
        targets.append(mirror)
    targets.extend(cfg.get("mobile_copy_dirs", []))
    for d in targets:
        try:
            if html is None:
                html = render_html(entries, cfg)
            os.makedirs(d, exist_ok=True)
            path = os.path.join(d, MOBILE_FILENAME)
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            results.append((path, None))
        except OSError as e:
            results.append((os.path.join(d, MOBILE_FILENAME), str(e)))
    if mirror:
        try:
            os.makedirs(os.path.join(mirror, INBOX_DIRNAME), exist_ok=True)
        except OSError:
            pass
    return results


_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#0d0d0d">
<title>Work Hours</title>
<style>
:root{--bg:#0d0d0d;--panel:#161616;--field:#1f1f1f;--mint:#3ddc97;--txt:#e8e8e8;
--muted:#8a8a8a;--red:#ff6b6b;--mintdark:#062019;--soft:#12291f}
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent;min-width:0}
html,body{max-width:100%;overflow-x:hidden}
body{background:var(--bg);color:var(--txt);font:15px/1.45 "Segoe UI",system-ui,sans-serif;
padding-bottom:76px}
header{padding:18px 16px 8px}
header h1{color:var(--mint);font-size:21px}
header .sub{color:var(--muted);font-size:12px;margin-top:2px}
#content{padding:8px 14px 20px}
.card{background:var(--panel);border-radius:14px;padding:13px 14px;margin-bottom:10px}
.row{display:flex;justify-content:space-between;align-items:baseline;gap:8px;flex-wrap:wrap}
.badge{font-size:11px;color:var(--mint);background:var(--soft);border-radius:99px;
padding:2px 9px;white-space:nowrap}
.money{color:var(--mint);font-weight:700}
.muted{color:var(--muted);font-size:12px}
.bullets{white-space:pre-wrap;color:var(--muted);font-size:13px;margin-top:8px;
border-top:1px solid #242424;padding-top:8px;display:none}
.card.open .bullets{display:block}
select,input,textarea{width:100%;background:var(--field);color:var(--txt);border:0;
border-radius:10px;padding:11px 12px;font:inherit;outline:none;accent-color:var(--mint)}
select:focus,input:focus,textarea:focus{box-shadow:0 0 0 1.5px var(--mint)}
label{display:block;color:var(--muted);font-size:12px;margin:12px 0 4px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.btn{display:block;width:100%;border:0;border-radius:12px;padding:13px;margin-top:12px;
font:600 15px "Segoe UI",system-ui,sans-serif;cursor:pointer;background:var(--panel);
color:var(--mint)}
.btn.primary{background:var(--mint);color:var(--mintdark)}
.tiles{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px}
.tile{background:var(--panel);border-radius:14px;padding:12px}
.tile .v{color:var(--mint);font-size:20px;font-weight:700;margin-top:2px}
.tile .l{color:var(--muted);font-size:11px}
.chartwrap{overflow-x:auto;background:var(--panel);border-radius:14px;padding:12px;
margin-bottom:12px}
.chartwrap h3{font-size:13px;color:var(--txt);margin-bottom:6px}
nav{position:fixed;left:0;right:0;bottom:0;display:flex;background:var(--panel);
border-top:1px solid #242424;padding-bottom:env(safe-area-inset-bottom)}
nav button{flex:1;background:none;border:0;color:var(--muted);font:12px "Segoe UI",sans-serif;
padding:9px 0 10px;cursor:pointer}
nav button .ic{display:block;font-size:19px;margin-bottom:1px}
nav button.on{color:var(--mint)}
.totalbar{display:grid;grid-template-columns:repeat(4,1fr);gap:4px;background:var(--soft);
border-radius:12px;padding:10px 6px;margin:10px 0;text-align:center}
.totalbar .v{color:var(--mint);font-weight:700;font-size:13.5px;overflow-wrap:anywhere}
.totalbar .l{color:var(--muted);font-size:10px}
.status{margin-top:10px;font-size:13px;color:var(--muted);white-space:pre-wrap}
.status.ok{color:var(--mint)} .status.err{color:var(--red)}
table.inv{width:100%;border-collapse:collapse;font-size:12.5px;margin:8px 0 14px}
table.inv th{background:#1f2a50;color:#fff;text-align:left;padding:7px 8px}
table.inv td{padding:6px 8px;border-bottom:1px solid #e5e7eb}
table.inv tr.tot td{background:#2f4b9e;color:#fff;font-weight:700;border:0}
table.inv th.r,table.inv td.r{text-align:right}
#printview{display:none;background:#fff;color:#111827;min-height:100vh;padding:20px 18px}
#printview h2{font-size:15px;margin:16px 0 6px}
#printview .lbl{color:#6b7280;font-size:10px;font-weight:700;letter-spacing:.4px}
#printview .big{font-size:26px;font-weight:800;text-align:right}
#printview .meta{color:#6b7280;font-size:12px;text-align:right}
#printview .meta b{color:#111827}
#printview .fromgrid{display:flex;justify-content:space-between;gap:12px}
#printview .foot{color:#6b7280;font-style:italic;font-size:10.5px;margin-top:8px}
#printview tr.wknd td{background:#e7f5ee}
#printview tr.alt td{background:#eef1f8}
.printbar{position:sticky;top:0;background:var(--mint);color:var(--mintdark);
padding:10px 14px;font-weight:600;display:flex;justify-content:space-between;gap:10px}
.printbar button{border:0;background:var(--mintdark);color:var(--mint);border-radius:8px;
padding:6px 12px;font-weight:600}
@media print{ .printbar,header,nav,#content{display:none!important}
 #printview{display:block!important;padding:0} body{background:#fff;padding:0} }
details{margin-top:12px}
summary{color:var(--muted);font-size:13px;cursor:pointer}
</style>
</head>
<body>
<script id="whdata" type="application/json">__WH_DATA__</script>

<header>
  <h1 id="hdr">⏱ Work Hours</h1>
  <div class="sub" id="sub"></div>
</header>
<div id="content"></div>
<div id="printview"></div>

<nav id="nav">
  <button data-tab="sheet"><span class="ic">📋</span>Timesheet</button>
  <button data-tab="dash"><span class="ic">📊</span>Dashboard</button>
  <button data-tab="inv"><span class="ic">📄</span>Invoice</button>
  <button data-tab="log"><span class="ic">✏️</span>Log</button>
</nav>

<script>
"use strict";
const D = JSON.parse(document.getElementById("whdata").textContent);
const GBP = n => n==null ? "No rate" : "£" + n.toLocaleString("en-GB",{minimumFractionDigits:2,maximumFractionDigits:2});
const MONTHS = ["January","February","March","April","May","June","July","August",
"September","October","November","December"];
const $ = s => document.querySelector(s);

document.getElementById("sub").textContent = "Data from PC: " + D.generated;

// ---------- calculations (mirror of the desktop logic) ----------
function hm(t){ if(!t) return null; const [h,m]=t.split(":").map(Number); return h*60+m; }
function hoursWorked(e){
  const s=hm(e.s), f=hm(e.f);
  if(s==null||f==null) return 0;
  return (f-s)/60 - (e.b||0)/60;
}
function totalHours(e){ return hoursWorked(e) + (e.o||0); }
function rateFor(dstr){
  let r=null;
  for(const x of D.rates) if(x.d<=dstr) r=x.r;
  return r;
}
function pay(e){ const r=rateFor(e.d); return r==null?null:Math.round(totalHours(e)*r*100)/100; }
function totalPay(es){ return es.some(e=>pay(e)==null)?null:es.reduce((a,e)=>a+pay(e),0); }
function mkey(dstr){ return dstr.slice(0,7); }               // "2026-06"
function mlabel(k){ const [y,m]=k.split("-"); return MONTHS[+m-1]+" "+y; }
function mshort(k){ const [y,m]=k.split("-"); return MONTHS[+m-1].slice(0,3)+" "+y.slice(2); }
function dayName(dstr){ return new Date(dstr+"T12:00:00").toLocaleDateString("en-GB",{weekday:"long"}); }
function taxYear(dstr){ const d=new Date(dstr+"T12:00:00");
  return (d.getMonth()+1)*100+d.getDate() >= 406 ? d.getFullYear() : d.getFullYear()-1; }
function months(){ return [...new Set(D.entries.map(e=>mkey(e.d)))].sort(); }
function entriesFor(k){ return D.entries.filter(e=>mkey(e.d)===k); }
function lastDayOf(k){ const [y,m]=k.split("-").map(Number); return new Date(y,m,0).getDate(); }

// ---------- tabs ----------
const TABS=["sheet","dash","inv","log"];
let TAB=TABS.includes(location.hash.slice(1))?location.hash.slice(1):"sheet";
let SEL=months().length?months()[months().length-1]:null;
document.getElementById("nav").addEventListener("click",ev=>{
  const b=ev.target.closest("button"); if(!b) return;
  TAB=b.dataset.tab;
  try{ history.replaceState(null,"","#"+TAB); }catch(e){}
  render();
});
function monthSelect(id){
  const opts=months().map(k=>`<option value="${k}" ${k===SEL?"selected":""}>${mlabel(k)}</option>`).join("");
  return `<select id="${id}">${opts}</select>`;
}

function render(){
  $("#printview").style.display="none";
  $("#content").style.display="";
  $("header").style.display="";
  $("#nav").style.display="";
  document.querySelectorAll("nav button").forEach(b=>b.classList.toggle("on",b.dataset.tab===TAB));
  ({sheet:renderSheet,dash:renderDash,inv:renderInv,log:renderLog})[TAB]();
}

// ---------- timesheet ----------
function renderSheet(){
  if(!SEL){ $("#content").innerHTML='<div class="card">No entries yet.</div>'; return; }
  const es=entriesFor(SEL);
  const th=es.reduce((a,e)=>a+hoursWorked(e),0), to=es.reduce((a,e)=>a+(e.o||0),0);
  const tt=es.reduce((a,e)=>a+totalHours(e),0), tp=totalPay(es);
  const cards=es.map((e,i)=>{
    const wk=e.t.includes("Weekend");
    const d=new Date(e.d+"T12:00:00");
    const dl=d.toLocaleDateString("en-GB",{weekday:"short",day:"2-digit",month:"short"});
    const time=e.s?`${e.s}–${e.f||"?"}${e.b?" · "+e.b+"m break":""}`:"—";
    return `<div class="card" onclick="this.classList.toggle('open')">
      <div class="row"><b>${dl}</b><span class="money">${GBP(pay(e))}</span></div>
      <div class="row"><span class="muted">${time} · ${totalHours(e).toFixed(1)} h${e.o?" (OT "+e.o+")":""}</span>
      <span class="badge"${wk?' style="background:#1d3a2c"':""}>${esc(e.t)}</span></div>
      <div class="bullets">${esc(e.su)||"—"}</div></div>`;
  }).join("");
  $("#content").innerHTML = monthSelect("msel") +
    `<div class="totalbar">
      <div><div class="v">${th.toFixed(1)}</div><div class="l">HOURS</div></div>
      <div><div class="v">${to.toFixed(1)}</div><div class="l">OVERTIME</div></div>
      <div><div class="v">${tt.toFixed(1)}</div><div class="l">TOTAL</div></div>
      <div><div class="v">${GBP(tp)}</div><div class="l">PAY</div></div>
    </div>` + cards +
    `<div class="muted" style="text-align:center;margin-top:6px">tap a day to see its summary</div>`;
  $("#msel").onchange=e=>{ SEL=e.target.value; render(); };
}
function esc(s){ return String(s??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;"); }

// ---------- dashboard ----------
function barChart(title, pairs, fmt){
  const max=Math.max(...pairs.map(p=>p[1]),1);
  const bw=44, gap=14, H=150, base=118;
  const W=Math.max(pairs.length*(bw+gap)+10, 280);
  const bars=pairs.map((p,i)=>{
    const h=Math.max(2, p[1]/max*92), x=8+i*(bw+gap);
    return `<rect x="${x}" y="${base-h}" width="${bw}" height="${h}" rx="5" fill="#3ddc97"/>
    <text x="${x+bw/2}" y="${base-h-6}" text-anchor="middle" fill="#3ddc97" font-size="10.5" font-weight="700">${fmt(p[1])}</text>
    <text x="${x+bw/2}" y="${base+16}" text-anchor="middle" fill="#8a8a8a" font-size="10">${p[0]}</text>`;
  }).join("");
  return `<div class="chartwrap"><h3>${title}</h3>
   <svg width="${W}" height="${H}" role="img">${bars}</svg></div>`;
}
function renderDash(){
  const ms=months();
  const now=new Date(); const ck=now.toISOString().slice(0,7);
  const pk=new Date(now.getFullYear(),now.getMonth()-1,15).toISOString().slice(0,7);
  const sum=(k,f)=>entriesFor(k).reduce((a,e)=>a+f(e),0);
  const ty=taxYear(now.toISOString().slice(0,10));
  const typay=totalPay(D.entries.filter(e=>taxYear(e.d)===ty));
  const days=D.entries.length;
  $("#content").innerHTML =
    `<div class="tiles">
      <div class="tile"><div class="l">THIS MONTH</div><div class="v">${sum(ck,totalHours).toFixed(1)} h</div></div>
      <div class="tile"><div class="l">LAST MONTH</div><div class="v">${sum(pk,totalHours).toFixed(1)} h</div></div>
      <div class="tile"><div class="l">TAX YEAR ${ty}/${String(ty+1).slice(2)} GROSS</div><div class="v">${GBP(typay)}</div></div>
      <div class="tile"><div class="l">DAYS LOGGED</div><div class="v">${days}</div></div>
    </div>` +
    barChart("Total hours / month", ms.map(k=>[mshort(k), sum(k,totalHours)]), v=>v.toFixed(0)) +
    (ms.some(k=>totalPay(entriesFor(k))==null)?'<div class="card muted">Add rates on the desktop to calculate pay.</div>':
    barChart("Pay / month", ms.map(k=>[mshort(k), Math.round(totalPay(entriesFor(k)))]), v=>"£"+v.toLocaleString("en-GB")));
}

// ---------- invoice ----------
function groups(k){
  const out=[], idx={};
  for(const e of entriesFor(k)){
    const r=rateFor(e.d); if(r==null) continue;
    if(!(r in idx)){ idx[r]=out.length; out.push({r,h:0,a:0}); }
    const g=out[idx[r]]; g.h+=totalHours(e); g.a+=pay(e);
  }
  return out;
}
function renderInv(){
  if(!SEL){ $("#content").innerHTML='<div class="card">No entries yet.</div>'; return; }
  if(entriesFor(SEL).some(e=>rateFor(e.d)==null)){
    $("#content").innerHTML=monthSelect("isel")+'<div class="card">Add a rate for every date on the desktop before creating an invoice.</div>';
    $("#isel").onchange=e=>{ SEL=e.target.value; render(); }; return;
  }
  const gs=groups(SEL), tot=gs.reduce((a,g)=>a+g.a,0), th=gs.reduce((a,g)=>a+g.h,0);
  const rows=gs.map(g=>`<tr><td>Contract hours worked @ £${g.r.toFixed(2)}/hour</td>
    <td class="r">${g.h.toFixed(1)}</td><td class="r">${g.r.toFixed(2)}</td>
    <td class="r">${g.a.toFixed(2)}</td></tr>`).join("");
  $("#content").innerHTML = monthSelect("isel") +
    `<div class="card"><table class="inv">
      <tr><th>Charge</th><th class="r">Hours</th><th class="r">Rate</th><th class="r">£</th></tr>
      ${rows}<tr class="tot"><td>Total due</td><td class="r">${th.toFixed(1)}</td><td></td>
      <td class="r">${GBP(tot)}</td></tr></table>
      <label>Invoice number</label><input id="invno" type="number" min="1" value="${esc(D.invoice.next_number)}">
      <button class="btn primary" onclick="showInvoice()">Open printable invoice</button>
      <div class="muted" style="margin-top:8px">Opens a print view — use your browser's
      Share / Print → “Save as PDF”. For the official PDF, generate it on the PC.</div>
      ${D.includesInvoiceDetails?'':'<div class="muted" style="margin-top:8px">Personal, client and payment details were excluded. Enable invoice details in desktop Settings only if you want them in this file.</div>'}
    </div>`;
  $("#isel").onchange=e=>{ SEL=e.target.value; render(); };
}
function showInvoice(){
  const k=SEL, no=$("#invno").value||"?", p=D.personal, bt=(D.bill_to.lines||[]);
  if(!/^\d+$/.test(no)||Number(no)<1){ alert("Enter a positive invoice number."); return; }
  const es=entriesFor(k), gs=groups(k);
  const tot=gs.reduce((a,g)=>a+g.a,0), th=gs.reduce((a,g)=>a+g.h,0);
  const today=new Date().toLocaleDateString("en-GB",{day:"numeric",month:"long",year:"numeric"});
  const notes=[];
  if(es.some(e=>e.t.includes("Weekend"))) notes.push("Weekend entries were worked remotely.");
  if(gs.length>1){
    const last=gs[gs.length-1].r;
    const sw=es.filter(e=>rateFor(e.d)===last).map(e=>e.d).sort()[0];
    const swd=new Date(sw+"T12:00:00");
    notes.push(`The contract rate changed from £${gs[0].r.toFixed(2)} to £${last.toFixed(2)} per hour from `+
      swd.toLocaleDateString("en-GB",{day:"numeric",month:"long",year:"numeric"})+" onwards.");
  }
  const detail=es.map((e,i)=>{
    const d=new Date(e.d+"T12:00:00"), r=rateFor(e.d)||0;
    const cls=e.t.includes("Weekend")?"wknd":(i%2?"alt":"");
    return `<tr class="${cls}"><td>${d.getDate()} ${MONTHS[d.getMonth()].slice(0,3)}</td>
     <td>${dayName(e.d)}</td><td>${esc(e.t)}</td><td class="r">${totalHours(e).toFixed(1)}</td>
     <td class="r">${r.toFixed(2)}</td><td class="r">${pay(e).toFixed(2)}</td></tr>`;
  }).join("");
  $("#printview").innerHTML =
   `<div class="printbar"><span>Invoice preview</span><span>
     <button onclick="doPrint()">🖨 Print / PDF</button>
     <button onclick="render()">✕ Back</button></span></div>
    <div class="fromgrid"><div>
      <div class="lbl">FROM</div><b>${esc(p.name)}</b><br>
      ${(p.address_lines||[]).map(esc).join("<br>")}<br>${esc(p.email)}<br>${esc(p.phone)}
    </div><div>
      <div class="big">INVOICE</div>
      <div class="meta">Invoice no. <b>${esc(no)}</b><br>Invoice date <b>${today}</b><br>
      Period <b>1–${lastDayOf(k)} ${mlabel(k)}</b></div>
    </div></div>
    <div style="border-top:1px solid #c9d2e8;margin-top:12px;padding-top:8px">
      <div class="lbl">BILL TO</div><b>${esc(bt[0]||"")}</b><br>${bt.slice(1).map(esc).join("<br>")}
    </div>
    <h2>Summary of charges</h2>
    <table class="inv"><tr><th>Charge</th><th class="r">Hours</th><th class="r">Rate (£/hr)</th><th class="r">Amount (£)</th></tr>
     ${gs.map(g=>`<tr><td>Contract hours worked @ £${g.r.toFixed(2)}/hour</td><td class="r">${g.h.toFixed(1)}</td>
     <td class="r">${g.r.toFixed(2)}</td><td class="r">${g.a.toFixed(2)}</td></tr>`).join("")}
     <tr class="tot"><td>Total due</td><td></td><td></td><td class="r">${GBP(tot)}</td></tr></table>
    <h2>Timesheet detail</h2>
    <table class="inv"><tr><th>Date</th><th>Day</th><th>Description</th><th class="r">Hours</th>
     <th class="r">Rate (£/hr)</th><th class="r">Amount (£)</th></tr>${detail}
     <tr class="tot"><td>TOTAL</td><td></td><td></td><td class="r">${th.toFixed(1)}</td><td></td>
     <td class="r">${tot.toFixed(2)}</td></tr></table>
    <div class="foot">${notes.join(" ")}</div>
    <h2>Payment</h2>
    <div class="lbl">PAYMENT DETAILS</div>
    Account name: <b>${esc(D.payment.account_name)}</b><br>
    Sort code: <b>${esc(D.payment.sort_code)}</b> &nbsp; Account no.: <b>${esc(D.payment.account_no)}</b>
    <p style="margin-top:8px;font-size:12.5px">${esc((D.invoice.thanks||"").replace("{number}",no))}</p>
    <div class="foot">${esc(D.invoice.self_note)}</div>`;
  $("#content").style.display="none";
  $("header").style.display="none";
  $("#nav").style.display="none";
  $("#printview").style.display="block";
  window.scrollTo(0,0);
}
function doPrint(){
  if(window.AndroidBridge && AndroidBridge.print){ AndroidBridge.print(); }
  else{ window.print(); }
}

// ---------- log ----------
function renderLog(){
  const t=new Date(); const today=t.toISOString().slice(0,10);
  const df=D.defaults||{};
  $("#content").innerHTML = `<div class="card">
    <label>Date</label><input id="ld" type="date" value="${today}">
    <div class="grid2"><div><label>Start</label><input id="ls" value="${esc(df.start??"09:00")}"></div>
    <div><label>Finish</label><input id="lf" value="${esc(df.finish??"17:30")}"></div></div>
    <div class="grid2"><div><label>Break (min)</label><input id="lb" type="number" value="${esc(df.break_min??"30")}"></div>
    <div><label>Overtime (hrs)</label><input id="lo" type="number" step="0.5" value="0"></div></div>
    <label>Type</label><select id="lt">${D.types.map(x=>`<option${x===(df.type||"")?" selected":""}>${esc(x)}</option>`).join("")}</select>
    <div class="totalbar" id="lprev"></div>
    <label>Rough notes</label><textarea id="lraw" rows="3" placeholder="what did you do today?"></textarea>
    <div class="muted" style="margin-top:8px">Write your summary below. Optional AI summaries are available in the desktop app; this companion stays offline and never stores an API key.</div>
    <label>Bullet summary (editable)</label><textarea id="lsum" rows="4" placeholder="• …"></textarea>
    <button class="btn primary" id="lsend">📤 Send to PC (via OneDrive)</button>
    <div class="status" id="lst"></div>
    <details><summary>How sending works</summary>
      <div class="muted" style="margin-top:6px">
      <b>Send to PC:</b> this saves a small file — share/save it into
      <b>${esc(D.inboxLabel)}</b>. The PC app asks you to confirm the import
      next time it opens (or via “Import phone entries” on the Timesheet tab).
      The exported file includes your work notes and is not encrypted.</div>
    </details></div>`;
  const upd=()=>{
    const e=readForm(); if(!e){ $("#lprev").innerHTML=""; return; }
    const r=rateFor(e.d);
    $("#lprev").innerHTML=`<div><div class="v">${hoursWorked(e).toFixed(1)}</div><div class="l">HOURS</div></div>
      <div><div class="v">${(e.o||0).toFixed(1)}</div><div class="l">OT</div></div>
      <div><div class="v">${totalHours(e).toFixed(1)}</div><div class="l">TOTAL</div></div>
      <div><div class="v">${r==null?"?":GBP(pay(e))}</div><div class="l">PAY</div></div>`;
  };
  ["ld","ls","lf","lb","lo","lt"].forEach(id=>{ $("#"+id).oninput=upd; $("#"+id).onchange=()=>{
    if(id==="lt" && $("#lt").value.includes("Weekend")){ $("#ls").value="";$("#lf").value="";$("#lb").value="";
      st("Weekend: leave times blank, put hours in Overtime.",""); } upd(); };});
  upd();
  $("#lsend").onclick=sendEntry;
}
function st(msg,cls){ const el=$("#lst"); el.textContent=msg; el.className="status "+cls; }
function readForm(){
  const d=$("#ld").value; if(!d) return null;
  const norm=v=>{ v=(v||"").trim(); if(!v) return null;
    const m=v.replace(".",":").match(/^(\d{1,2}):?(\d{2})?\s*(am|pm)?$/i); if(!m) return null;
    let h=+m[1]; const mi=m[2]?+m[2]:0, ap=(m[3]||"").toLowerCase();
    if(ap==="pm"&&h<12)h+=12; if(ap==="am"&&h===12)h=0;
    if(h>23||mi>59) return null;
    return String(h).padStart(2,"0")+":"+String(mi).padStart(2,"0"); };
  return { d, s:norm($("#ls").value), f:norm($("#lf").value),
    b:$("#lb").value?+$("#lb").value:null, o:+($("#lo").value||0),
    t:$("#lt").value, su:$("#lsum").value.trim() };
}
async function sendEntry(){
  const e=readForm();
  if(!e){ st("Enter a date first.","err"); return; }
  if(($("#ls").value.trim()&&!e.s)||($("#lf").value.trim()&&!e.f)){
    st("Use valid start and finish times, such as 09:00 and 17:30.","err"); return;
  }
  if(!e.su) e.su=$("#lraw").value.trim()||"• No tasks recorded";
  if((e.s==null)!=(e.f==null) || (e.s&&e.f&&(e.f<=e.s||hoursWorked(e)<0)) ||
      !Number.isFinite(e.o)||e.o<0||e.o>24 || (e.b!=null&&(!Number.isInteger(e.b)||e.b<0||e.b>1440))){
    st("Check the shift: both times are needed; finish after start; break within the shift; overtime 0–24 hours.","err"); return;
  }
  const body=JSON.stringify({app:"work-hours-tracker",version:1,date:e.d,start:e.s,finish:e.f,
    break_min:e.b,overtime:e.o,type:e.t,summary:e.su},null,1);
  const name="whentry_"+e.d.replace(/-/g,"")+"_"+Date.now()+".json";
  if(window.AndroidBridge && AndroidBridge.shareEntry){
    AndroidBridge.shareEntry(name, body);
    st("Choose OneDrive and save into "+D.inboxLabel+". Confirm the import on the PC. ✓","ok");
    return;
  }
  const file=new File([body],name,{type:"application/json"});
  if(navigator.canShare && navigator.canShare({files:[file]})){
    try{ await navigator.share({files:[file],title:"Work Hours entry"});
      st("Now choose OneDrive and save it in "+D.inboxLabel+". Confirm the import on the PC. ✓","ok");
      return; }catch(err){ if(err.name==="AbortError"){ st("Share cancelled.",""); return; } }
  }
  const a=document.createElement("a");
  a.href=URL.createObjectURL(new Blob([body],{type:"application/json"}));
  a.download=name; a.click();
  st("Downloaded "+name+". Move it into "+D.inboxLabel+" so the PC can import it.","ok");
}

render();
</script>
</body>
</html>
"""
