import { Decoder, IMessage, iter_decoded_log_format } from "./decoder";
import "./style.css";
import { requestToHandler, sendEventToClient, nextMessageSeq, IEventMessage} from "./vscodeComm";

// Interesting reads:
// https://medium.com/metaphorical-web/javascript-treeview-controls-devil-in-the-details-74c252e00ed8
// https://iamkate.com/code/tree-views/
// https://stackoverflow.com/questions/10813581/can-i-replace-the-expand-icon-of-the-details-element

interface IContentAdded {
    ul: HTMLElement;
    li: HTMLElement;
    details: HTMLElement;
    summary: HTMLElement;
    span: HTMLElement;
}

function addContainer(
    opts: IOpts,
    parent: IContentAdded,
    content: string,
    decodedMessage: IMessage,
    open: boolean
): IContentAdded {
    // <li>
    //   <details open>
    //     <summary>
    //          <span></span>
    //     </summary>
    //     <ul>
    //     </ul>
    //   </details>
    // </li>

    const li: HTMLLIElement = document.createElement("li");
    const details: HTMLDetailsElement = document.createElement("details");
    details.open = open;
    const summary = document.createElement("summary");

    const ul = document.createElement("ul");
    li.appendChild(details);
    details.appendChild(summary);
    details.appendChild(ul);
    parent.ul.appendChild(li);

    const span: HTMLSpanElement = document.createElement("span");
    span.setAttribute("role", "button");
    span.textContent = content;
    summary.appendChild(span);

    if (opts.onClickReference) {
        span.classList.add("span_link");
        span.onclick = (ev) => {
            ev.preventDefault();
            opts.onClickReference(decodedMessage);
        };
    }

    return { ul, li, details, summary, span };
}

function addStatus(summary: HTMLElement, status: string) {
    const span = document.createElement("span");
    span.textContent = status;
    span.classList.add("label");
    span.classList.add(status.replace(" ", "_"));
    summary.insertBefore(span, summary.firstChild);
}

interface IOpts {
    outputFileContents: string;
    filterLevel: "FAIL" | "WARN" | "PASS";
    viewMode: "hierarchy" | "flat";
    onClickReference: Function | undefined;
}

function acceptStatus(opts: IOpts, status: string) {
    switch (opts.filterLevel) {
        case "FAIL":
            return status == "FAIL" || status == "ERROR";
        case "WARN":
            return status == "FAIL" || status == "ERROR" || status == "WARN";
        case "PASS":
            return true;
    }
}

let lastOpts: IOpts | undefined = undefined;

export function updateFilterLevel(filterLevel: "FAIL" | "WARN" | "PASS") {
    if (!lastOpts) {
        return;
    }
    if (lastOpts.filterLevel !== filterLevel) {
        lastOpts.filterLevel = filterLevel;
        main(lastOpts);
    }
}

function main(opts: IOpts) {
    lastOpts = opts;
    const mainDiv: HTMLElement = document.getElementById("mainTree");
    mainDiv.replaceChildren(); // clear all children

    const rootUl = document.createElement("ul");
    rootUl.classList.add("tree");
    mainDiv.appendChild(rootUl);

    const decoder = new Decoder();
    let parent: IContentAdded = {
        "ul": rootUl,
        "li": undefined,
        "details": undefined,
        "summary": undefined,
        "span": undefined,
    };
    const stack = [];
    stack.push(parent);
    let suiteName = "";
    for (const msg of iter_decoded_log_format(opts.outputFileContents)) {
        switch (msg.message_type) {
            case "SS":
                // start suite
                suiteName = msg.decoded["name"] + ".";
                // parent = addContainer(opts, parent, msg.decoded["name"], msg, true);
                // stack.push(parent);
                break;

            case "ST":
                // start test
                parent = addContainer(opts, parent, suiteName + msg.decoded["name"], msg, false);
                stack.push(parent);
                break;
            case "SK":
                // start keyword
                let libname = msg.decoded["libname"];
                if (libname) {
                    libname += ".";
                }
                parent = addContainer(
                    opts,
                    parent,
                    `${msg.decoded["keyword_type"]} - ${libname}${msg.decoded["name"]}`,
                    msg,
                    false
                );
                stack.push(parent);
                break;
            case "ES": // end suite
                suiteName = "";
                break;
            case "ET": // end test
            case "EK": // end keyword
                const status = msg.decoded["status"];
                if (acceptStatus(opts, status)) {
                    const summary = parent.summary;
                    addStatus(summary, status);
                } else {
                    parent.li.remove();
                }

                stack.pop();
                parent = stack.at(stack.length - 1);
                break;
            case "KA":
                const item: IContentAdded = stack.at(-1);
                item.span.textContent += ` | ${msg.decoded}`;
                break;
        }
    }

    return main;
}

function onClickReference(message) {
    let ev: IEventMessage = {
        type: "event",
        seq: nextMessageSeq(),
        event: "onClickReference",
    };
    ev["data"] = message;
    sendEventToClient(ev);
}

let lastContents = undefined;

requestToHandler["setContents"] = function setContents(msg) {
    lastContents = msg.outputFileContents;
    main({
        outputFileContents: msg.outputFileContents,
        filterLevel: "PASS",
        viewMode: "flat",
        onClickReference: onClickReference,
    });
};

function onChangedFilterLevel() {
    const filterLevel = document.getElementById("filterLevel");
    const value: "FAIL" | "WARN" | "PASS" = <"FAIL" | "WARN" | "PASS">(<HTMLSelectElement>filterLevel).value;
    updateFilterLevel(value);
}

function onChangedRun() {}
window["onChangedRun"] = onChangedRun;
window["onChangedFilterLevel"] = onChangedFilterLevel;
