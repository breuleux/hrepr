$$HREPR = {
    scriptStatus: {},
    counters: {},
    fromHTML(html) {
        const node = document.createElement("div");
        node.innerHTML = html;
        return node.childNodes[0];
    },
    prepare(node_id) {
        const self = document.getElementById(node_id);
        let resolve = null;
        self.__object = new Promise((rs, rj) => { resolve = rs });
        self.__object.__resolve = resolve;
        return self;
    },
    swap(orig, repl) {
        if (repl) {
            if (repl.getElement) {
                repl = repl.getElement();
            }
            if (repl instanceof HTMLElement) {
                repl.__object = orig.__object;
                repl.setAttribute("id", orig.getAttribute("id"));
                orig.replaceWith(repl);
            }
            else {
                orig.remove();
            }
        }
    },
    isFunc(x) {
        let hasprop = prop => Object.getOwnPropertyNames(x).includes(prop);
        return (hasprop("arguments") || !hasprop("prototype"));
    },
    loadScripts(scripts, cb) {
        if (scripts.length == 0) {
            cb();
            return;
        }
        const counter = {count: scripts.length, callback: cb};
        for (let script of scripts) {
            let counters = (this.counters[script] ||= []);
            counters.push(counter);
            if (this.scriptStatus[script] === undefined) {
                this.scriptStatus[script] = false;
                function onLoad() {
                    $$HREPR.scriptStatus[script] = true;
                    $$HREPR.triggerScript(script);
                }
                let scriptTag = document.createElement("script");
                scriptTag.src = script;
                scriptTag.onload = onLoad;
                document.head.appendChild(scriptTag);    
            }
            else if (this.scriptStatus[script]) {
                $$HREPR.triggerScript(script);
            }
        }
    },
    triggerScript(script) {
        for (let counter of this.counters[script] || []) {
            counter.count--;
            if (!counter.count) {
                counter.callback();
            }
        }
    },
    ucall(obj, sym, ...arglist) {
        if (sym) {
            return $$HREPR.isFunc(obj[sym]) ? obj[sym](...arglist) : new obj[sym](...arglist);
        }
        else {
            return $$HREPR.isFunc(obj) ? obj(...arglist) : new obj(...arglist);
        }
    },
}

