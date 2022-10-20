// Based on the python decoder example.
// Used: https://extendsclass.com/python-to-javascript.html

import parseISO from "date-fns/parseISO";

export interface IMessage {
    message_type: string;
    decoded: any;
}

function version_decode(decoder, message) {
    return { message };
}

function simple_decode(decoder, message) {
    return JSON.parse(message);
}

function decode_time(decoder, time) {
    decoder.initial_time = parseISO(time);
    return { time };
}

function decode_memo(decoder, message) {
    var memo_id, memo_value;
    const split = splitInChar(message, ":");
    if (split) {
        [memo_id, memo_value] = split;
        try {
            memo_value = JSON.parse(memo_value);
        } catch (error) {
            console.log("Error parsing json: " + memo_value);
            console.log(error);
            return null;
        }
        decoder.memo[memo_id] = memo_value;
    }

    return null;
}

function start_suite(decoder, message) {
    let ident = decoder.ident;
    decoder.level += 1;
    let [name_id, suite_id_id, suite_source_id, time_delta_in_seconds] = message.split("|");
    let name = decoder.memo[name_id];
    let suite_id = decoder.memo[suite_id_id];
    let source = decoder.memo[suite_source_id];
    return { name, suite_id, source, time_delta_in_seconds };
}

function end_suite(decoder, message) {
    var ident, status, status_id, time_delta_in_seconds;
    decoder.level -= 1;
    ident = decoder.ident;
    [status_id, time_delta_in_seconds] = message.split("|");
    status = decoder.memo[status_id];
    return { status, time_delta_in_seconds };
}

function start_task_or_test(decoder, message) {
    let ident = decoder.ident;
    decoder.level += 1;
    let [name_id, suite_id_id, lineno, time_delta_in_seconds] = message.split("|");
    let name = decoder.memo[name_id];
    let suite_id = decoder.memo[suite_id_id];
    lineno = parseInt(lineno);
    return { name, suite_id, lineno, time_delta_in_seconds };
}

function end_task_or_test(decoder, message) {
    var ident, message_id, status, status_id, time_delta_in_seconds;
    decoder.level -= 1;
    ident = decoder.ident;
    [status_id, message_id, time_delta_in_seconds] = message.split("|");
    status = decoder.memo[status_id];
    message = decoder.memo[message_id];
    return { status, message, time_delta_in_seconds };
}

function _decodeOid(decoder, oid) {
    return decoder.memo[oid];
}
function _decodeFloat(decoder, msg) {
    return parseInt(msg);
}
function _decodeInt(decoder, msg) {
    return parseFloat(msg);
}

function _decode(message_definiton) {
    const names = [];
    const nameToDecode = new Map();
    for (let s of message_definiton.split(",")) {
        s = s.trim();
        const i = s.indexOf(":");
        let decode = "oid";
        if (i != -1) {
            [s, decode] = s.split(":");
        }
        names.push(s);
        if (decode === "oid") {
            nameToDecode.set(s, _decodeOid);
        } else if (decode === "int") {
            nameToDecode.set(s, _decodeInt);
        } else if (decode === "float") {
            nameToDecode.set(s, _decodeFloat);
        } else {
            throw new Error("Unexpected: " + decode);
        }
    }

    function _decImpl(decoder, message) {
        const splitted = message.split("|");
        const ret = {};
        for (let index = 0; index < splitted.length; index++) {
            const s = splitted[index];
            const name = names[index];
            ret[name] = nameToDecode.get(name)(decoder, s);
        }
        console.log('decoded', ret)
        return ret;
    }
    return _decImpl;
}

const start_keyword = _decode(
    "name:oid, libname:oid, keyword_type:oid, doc:oid, source:oid, lineno:int, time_delta_in_seconds:float"
);

// function start_keyword(decoder, message) {
//     let ident = decoder.ident;
//     decoder.level += 1;
//     let [name_id, libname_id, type_id, doc_id, source_id, lineno, time_delta_in_seconds] = message.split("|");
//     let keyword_type = decoder.memo[type_id];
//     let name = decoder.memo[name_id];
//     let libname = decoder.memo[libname_id];
//     let doc = decoder.memo[doc_id];
//     let source = decoder.memo[source_id];
//     lineno = parseInt(lineno);
//     return { keyword_type, name, libname, doc, time_delta_in_seconds, source, lineno };
// }

function end_keyword(decoder, message) {
    var ident, status, status_id, time_delta_in_seconds;
    decoder.level -= 1;
    ident = decoder.ident;
    [status_id, time_delta_in_seconds] = message.split("|");
    status = decoder.memo[status_id];
    return { status, time_delta_in_seconds };
}

function keyword_argument(decoder, message) {
    return decoder.memo[message];
}

const _MESSAGE_TYPE_INFO = {
    "V": version_decode,
    "I": simple_decode,
    "T": decode_time,
    "M": decode_memo,
    "SS": start_suite,
    "ES": end_suite,
    "ST": start_task_or_test,
    "ET": end_task_or_test,
    "SK": start_keyword,
    "EK": end_keyword,
    "KA": keyword_argument,
};

export class Decoder {
    memo;
    initial_time;
    level;
    ident;

    constructor() {
        this.memo = {};
        this.initial_time = null;
        this.level = 0;
        this.ident = "";
    }

    decode_message_type(message_type, message) {
        var handler;
        handler = _MESSAGE_TYPE_INFO[message_type];
        return handler(this, message);
    }
}

function splitInChar(line: string, char: string) {
    const i = line.indexOf(char);
    if (i > 0) {
        const message_type = line.substring(0, i);
        const message = line.substring(i + 1);
        return [message_type, message];
    }
    return undefined;
}

export function* iter_decoded_log_format(stream: string) {
    var decoded, decoder, message, message_type;
    decoder = new Decoder();

    for (let line of stream.split(/\r?\n/)) {
        line = line.trim();

        if (line) {
            const split = splitInChar(line, " ");
            if (split) {
                [message_type, message] = split;
                decoded = decoder.decode_message_type(message_type, message);

                if (decoded) {
                    const m: IMessage = { "message_type": message_type, "decoded": decoded };
                    yield m;
                }
            }
        }
    }
}
