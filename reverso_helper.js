// reverso_helper.js
const Reverso = require("reverso-api");
const reverso = new Reverso();

let data = "";
process.stdin.on("data", (c) => (data += c));
process.stdin.on("end", async () => {
  try {
    const payload = JSON.parse(data || "{}");
    const text = String(payload.text || "").trim();
    const from = String(payload.from || "").toLowerCase().trim();
    const to = String(payload.to || "").toLowerCase().trim();
    const mode = (payload.mode || "translation").toLowerCase();

    if (!text || !from || !to) {
      process.stderr.write(JSON.stringify({ ok: false, message: "Missing text/from/to" }));
      process.exit(1);
      return;
    }

    let result;
    if (mode === "context") {
      result = await reverso.getContext(text, from, to);
    } else {
      result = await reverso.getTranslation(text, from, to);
    }

    process.stdout.write(JSON.stringify({ ok: true, mode, result }));
  } catch (err) {
    process.stderr.write(JSON.stringify({ ok: false, message: err?.message || String(err) }));
    process.exit(1);
  }
});
