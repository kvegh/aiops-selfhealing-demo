"use strict";

// Runs the actual page script with a small DOM and HTTP test harness. No npm
// packages are needed. This checks behavior, including repeated recovery and
// a participant losing the race to another press; it does not test rendering.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const root = path.resolve(__dirname, "..");
const shell = fs.readFileSync(path.join(root, "demo-web/index.html"), "utf8");
const content = fs.readFileSync(path.join(root, "demo-web/content.html"), "utf8");
const script = shell.match(/<script>([\s\S]*?)<\/script>/)[1];

function element() {
    const classes = new Set();
    return {
        innerHTML: "",
        textContent: "",
        classList: {
            add: (name) => classes.add(name),
            remove: (name) => classes.delete(name),
            contains: (name) => classes.has(name)
        }
    };
}

let button;
const elements = Object.fromEntries(
    ["stage", "notfound", "nf-note", "flash", "flash-text"].map((id) => [id, element()])
);
let stageHtml = "";
Object.defineProperty(elements.stage, "innerHTML", {
    get: () => stageHtml,
    set: (html) => {
        stageHtml = html;
        button = html.includes('id="panic-button"') ? {
            disabled: false,
            big: element(),
            small: element(),
            addEventListener: function (_, callback) { this.click = callback; },
            querySelector: function (selector) {
                return selector === ".pb-big" ? this.big : this.small;
            }
        } : null;
    }
});

const intervals = [];
let contentStatus = 200;
let armedStatus = 200;
let nonce = "first-round";
let panicStatus = 202;
const posts = [];
vm.runInNewContext(script, {
    Date,
    document: { getElementById: (id) => id === "panic-button" ? button : elements[id] },
    location: { reload: () => { throw new Error("A page refresh was attempted"); } },
    setTimeout: () => 0,
    setInterval: (callback, delay) => { intervals.push({ callback, delay }); return intervals.length; },
    fetch: async (url, options = {}) => {
        const route = url.split("?")[0];
        assert.equal(options.cache, "no-store");
        if (route === "/api/panic") {
            assert.equal(options.method, "POST");
            posts.push(JSON.parse(options.body));
            return { status: panicStatus, ok: panicStatus >= 200 && panicStatus < 300 };
        }
        const status = route === "armed" ? armedStatus : contentStatus;
        return { status, ok: status === 200, text: async () => route === "armed" ? nonce : content };
    }
});

const flush = async () => { await new Promise(setImmediate); await new Promise(setImmediate); };
const poll = async () => { intervals.forEach(({ callback }) => callback()); await flush(); };

async function run() {
    await flush();
    assert.equal(intervals.length, 2);
    intervals.forEach(({ delay }) => assert.equal(delay, 2000));
    assert.equal(button.disabled, false);

    panicStatus = 423;
    button.click();
    await flush();
    assert.equal(button.disabled, true);
    assert.equal(elements["flash-text"].textContent, "Someone beat you to it.");

    contentStatus = 404;
    armedStatus = 404;
    await poll();
    assert.equal(elements.stage.classList.contains("is-gone"), true);
    assert.equal(elements.notfound.classList.contains("is-shown"), true);

    contentStatus = 200;
    await poll();
    assert.equal(elements.stage.classList.contains("is-gone"), false);
    assert.equal(elements.notfound.classList.contains("is-shown"), false);
    assert.equal(button.disabled, true, "restored content must wait for server rearming");

    armedStatus = 200;
    nonce = "second-round";
    await poll();
    assert.equal(button.disabled, false);
    panicStatus = 202;
    button.click();
    await flush();
    assert.equal(posts.at(-1).nonce, "second-round");
    assert.equal(button.disabled, true);

    contentStatus = 404;
    armedStatus = 404;
    await poll();
    assert.equal(elements.notfound.classList.contains("is-shown"), true);
    contentStatus = 200;
    armedStatus = 200;
    nonce = "third-round";
    await poll();
    assert.equal(button.disabled, false);
    assert.equal(elements.notfound.classList.contains("is-shown"), false);
    console.log("PASS: automatic failure/recovery/rearm, repeated rounds, and a benign 423 race");
}

run().catch((error) => { console.error(error); process.exitCode = 1; });
