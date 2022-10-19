import { TextDecoder } from "util";
import * as vscode from "vscode";
import { OUTPUT_CHANNEL } from "../channel";
import { debounce } from "../common";
import { uriExists } from "../files";

interface IContents {
    isPlaceholder: boolean;
    html: string;
    afterHTMLSet?: any;
}

export class RobotOutputViewProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = "robot.view.output";

    private view?: vscode.WebviewView;
    private loading?: { cts: vscode.CancellationTokenSource };
    private extensionUri: vscode.Uri;
    private localResourceRoot: vscode.Uri = undefined;

    // We can use this as a place to store the run results we've seen.
    private storageUri: vscode.Uri = undefined;

    constructor(context: vscode.ExtensionContext) {
        this.extensionUri = context.extensionUri;
        this.storageUri = context.storageUri;
        context.subscriptions.push(
            vscode.window.onDidChangeActiveTextEditor(() => {
                this.update();
            })
        );

        this.update();
    }

    public resolveWebviewView(
        webviewView: vscode.WebviewView,
        context: vscode.WebviewViewResolveContext,
        token: vscode.CancellationToken
    ) {
        OUTPUT_CHANNEL.appendLine("Resolving Robot Output webview.");
        this.view = webviewView;
        this.finishInit(context, token);
    }

    private async finishInit(context: vscode.WebviewViewResolveContext, token: vscode.CancellationToken) {
        if (!this.localResourceRoot) {
            this.localResourceRoot = await getLocalResourceRoot(this.extensionUri);
        }
        const localResourceRoots = [];
        if (this.localResourceRoot) {
            localResourceRoots.push(this.localResourceRoot);
        }
        if (token.isCancellationRequested) {
            return;
        }

        const webviewView = this.view;
        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: localResourceRoots,
        };

        webviewView.onDidChangeVisibility(() => {
            this.update();
        });

        webviewView.onDidDispose(() => {
            this.view = undefined;
        });

        let html: string;
        try {
            const indexHTML: vscode.Uri = vscode.Uri.joinPath(this.localResourceRoot, "index.html");
            const indexContents: Uint8Array = await vscode.workspace.fs.readFile(indexHTML);
            if (token.isCancellationRequested) {
                return;
            }
            const decoded = new TextDecoder("utf-8").decode(indexContents);
            const scriptUri = this.view.webview.asWebviewUri(vscode.Uri.joinPath(this.localResourceRoot, "bundle.js"));
            html = decoded
                .replaceAll("return getDummyOutputFileContents();", "return '';")
                .replaceAll("bundle.js", scriptUri.toString())
                .replaceAll(
                    "onClickReference = console.log",
                    `onClickReference = (element)=>{
	                    console.log(element);
	                }
	                `
                );
        } catch (error) {
            html = "Error loading HTML: " + error;
        }
        webviewView.webview.html = html;

        this.update();
    }

    private async update() {
        this.updateDebounced();
    }

    updateDebounced = debounce(() => {
        this._doUpdate();
    }, 500);

    private async _doUpdate() {
        if (!this.view || !this.view.visible) {
            return;
        }

        if (this.loading) {
            this.loading.cts.cancel();
            this.loading = undefined;
        }

        const loadingEntry = { cts: new vscode.CancellationTokenSource() };
        this.loading = loadingEntry;

        const updatePromise = (async () => {
            if (this.loading !== loadingEntry) {
                return;
            }
            this.loading = undefined;

            if (this.view && this.view.visible) {
                this.setContentsInHTML(loadingEntry.cts.token, this.view.webview);
            }
        })();

        await Promise.race([
            updatePromise,

            new Promise<void>((resolve) => setTimeout(resolve, 250)).then(() => {
                if (loadingEntry.cts.token.isCancellationRequested) {
                    return;
                }
                return vscode.window.withProgress(
                    { location: { viewId: RobotOutputViewProvider.viewType } },
                    () => updatePromise
                );
            }),
        ]);
    }

    private async setContentsInHTML(token: vscode.CancellationToken, webview: vscode.Webview): Promise<IContents> {
        OUTPUT_CHANNEL.appendLine("Robot Output webview: set contents in HTML.");

        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            return;
        }

        if (token.isCancellationRequested) {
            return;
        }

        const filePath = editor.document.uri.fsPath;
        if (!filePath.endsWith(".xml") && !filePath.endsWith(".rfstream")) {
            return;
        }
        const currDoc = editor.document;

        let text = currDoc.getText();
        if (filePath.endsWith(".xml")) {
            // We need to convert it to the rfstream format first.
            const converted: string = await vscode.commands.executeCommand("robot.convertOutputXMLToRobostream", {
                "xml_contents": text,
            });
            if (token.isCancellationRequested) {
                return;
            }
            if (!converted) {
                return;
            }
            text = converted;
        }
        webview.postMessage({ command: "setContents", outputFileContents: text });
    }
}

async function getLocalResourceRoot(extensionUri: vscode.Uri): Promise<vscode.Uri | undefined> {
    let localResourceRoot = vscode.Uri.joinPath(extensionUri, "src", "robotframework_ls", "vendored", "output-webview");
    if (!(await uriExists(localResourceRoot))) {
        const checkUri = vscode.Uri.joinPath(extensionUri, "..", "robot-stream", "output-webview", "dist");
        if (!(await uriExists(checkUri))) {
            vscode.window.showErrorMessage(
                "Unable to find robot output webview in:\n[" +
                    localResourceRoot.fsPath +
                    "],\n[" +
                    checkUri.fsPath +
                    "]"
            );
            return;
        }
        localResourceRoot = checkUri;
    }
    return localResourceRoot;
}
