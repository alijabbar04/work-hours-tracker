// Execute the generated companion with a tiny DOM double. No browser/network,
// real user data, modules from npm, or persistent storage are used.
const fs = require("node:fs");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const html = fs.readFileSync(process.argv[2], "utf8");
const data = html.match(/<script id="whdata" type="application\/json">([\s\S]*?)<\/script>/)[1];
const source = html.split("<script>").at(-1).split("</script>")[0];
const nodes = new Map();
function node(id) {
  if (!nodes.has(id)) nodes.set(id, {
    textContent: id === "whdata" ? data : "", innerHTML: "", value: "", style: {},
    addEventListener() {}, classList: {toggle() {}},
  });
  return nodes.get(id);
}
const alerts = [];
const context = vm.createContext({
  document: {getElementById: node, querySelector: s => node(s.replace(/^#/, "")),
    querySelectorAll: () => []},
  location: {hash: ""}, history: {replaceState() {}},
  window: {scrollTo() {}, print() {}}, alert: msg => alerts.push(msg), console,
});
vm.runInContext(source, context);
assert.equal(node("content").innerHTML.includes("<img"), false, "timesheet type and summary escaped");
assert.match(node("content").innerHTML, /&lt;img/);
vm.runInContext("renderLog()", context);
assert.equal(node("content").innerHTML.includes('autofocus onfocus="'), false, "form attributes escaped");
assert.match(node("content").innerHTML, /&quot;/);
vm.runInContext("renderInv()", context);
node("invno").value = "7";
vm.runInContext("showInvoice()", context);
assert.equal(node("printview").innerHTML.includes("<img"), false, "invoice details escaped");
assert.match(node("printview").innerHTML, /&lt;img/);
node("invno").value = '<img src=x onerror="bad()">';
vm.runInContext("showInvoice()", context);
assert.equal(alerts.length, 1, "malformed invoice number rejected");
