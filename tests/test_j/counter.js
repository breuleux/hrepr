
class Counter {
    constructor(node, options) {
        this.node = node;
        this.increment = options.increment;
        this.current = 0;
        this.node.innerText = "Click me!";
        this.node.onclick = evt => {
            this.current += this.increment;
            this.node.innerText = this.current;
        }
    }
}

const bytwo = node => new Counter(node, {increment: 2});
const bythree = node => new Counter(node, {increment: 3});
const by = {
    two: bytwo,
    three: bythree
}
