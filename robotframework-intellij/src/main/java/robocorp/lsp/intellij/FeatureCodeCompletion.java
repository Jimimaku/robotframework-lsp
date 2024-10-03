/*
 * Original work Copyright (c) 2019, WSO2 Inc. (http://www.wso2.org) (Apache 2.0)
 * See ThirdPartyNotices.txt in the project root for license information.
 * All modifications Copyright (c) Robocorp Technologies Inc.
 * All rights reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License")
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http: // www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package robocorp.lsp.intellij;

import com.intellij.codeInsight.completion.*;
import com.intellij.codeInsight.lookup.AutoCompletionPolicy;
import com.intellij.codeInsight.lookup.LookupElement;
import com.intellij.codeInsight.lookup.LookupElementPresentation;
import com.intellij.codeInsight.template.TemplateManager;
import com.intellij.codeInsight.template.impl.TemplateImpl;
import com.intellij.codeInsight.template.impl.TextExpression;
import com.intellij.openapi.application.ex.ApplicationUtil;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.editor.Document;
import com.intellij.openapi.editor.Editor;
import com.intellij.openapi.editor.EditorModificationUtil;
import com.intellij.openapi.progress.EmptyProgressIndicator;
import com.intellij.openapi.progress.ProcessCanceledException;
import com.intellij.openapi.progress.ProgressIndicator;
import com.intellij.openapi.progress.ProgressIndicatorProvider;
import com.intellij.openapi.project.Project;
import com.intellij.openapi.util.TextRange;
import com.intellij.openapi.util.text.StringUtil;
import org.eclipse.lsp4j.*;
import org.eclipse.lsp4j.jsonrpc.messages.Either;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

import javax.swing.*;
import javax.swing.text.BadLocationException;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Iterator;
import java.util.List;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicReference;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

// https://intellij-support.jetbrains.com/hc/en-us/community/posts/360010327299-Code-completion-without-applying-initial-lookupString
// (Code-completion without applying initial lookupString)
public class FeatureCodeCompletion extends CompletionContributor {

    public static AutoCompletionPolicy AUTO_COMPLETION_POLICY = AutoCompletionPolicy.SETTINGS_DEPENDENT;

    private static final Logger LOG = Logger.getInstance(FeatureCodeCompletion.class);

    private static final AtomicReference<CompletableFuture<Either<List<CompletionItem>, CompletionList>>> currentCompletion = new AtomicReference<>();

    private static class SnippetVariable {
        String lspSnippetText;
        int startIndex;
        int endIndex;
        String variableValue;

        SnippetVariable(String text, int start, int end) {
            this.lspSnippetText = text;
            this.startIndex = start;
            this.endIndex = end;
            this.variableValue = getVariableValue(text);
        }

        private String getVariableValue(String lspVarSnippet) {
            if (lspVarSnippet.contains(":")) {
                return lspVarSnippet.substring(lspVarSnippet.indexOf(':') + 1, lspVarSnippet.lastIndexOf('}'));
            }
            return " ";
        }
    }

    public static class LSPPrefixMatcher extends PrefixMatcher {

        private final String normalizedPrefix;

        public static String getPrefix(String lineToCursor) {
            // This is really unfortunate. We have to add logic which should be in the language
            // server in the client as it seems there's no way to not have Intellij use that
            // info (even if doing so makes things wrong).
            // This is used both when applying a completion and even when Intellij tries
            // to be smart and applies a partial completion just based on the prefix
            // (i.e.: https://github.com/robocorp/robotframework-lsp/issues/248)
            // The logic below is only valid for the Robot Framework Language Server (other
            // language servers would need to have a custom logic here).
            FastStringBuffer buf = new FastStringBuffer(lineToCursor, 0);
            if (buf.length() == 0) {
                return "";
            }
            StringBuilder builder = new StringBuilder();
            if (buf.lastChar() == ' ') {
                buf.deleteLast();
                builder.append(' ');
            }
            // 2 spaces
            if (buf.lastChar() == ' ') {
                return "";
            }

            while (buf.length() > 0) {
                char c = buf.lastChar();
                buf.deleteLast();

                if (c == ' ' && (buf.length() == 0 || buf.lastChar() == ' ' || buf.lastChar() == '}')) {
                    // 2 spaces or a single space before the line end.
                    return builder.reverse().toString();
                }

                if (c == '.' || c == '/' || c == '{' || c == '$') {
                    return builder.reverse().toString();
                }
                builder.append(c);
            }
            if (builder.length() > 0) {
                return builder.reverse().toString();
            }
            return lineToCursor;
        }

        public LSPPrefixMatcher(String prefix) {
            super(prefix);
            normalizedPrefix = normalizeRobotName(myPrefix);
        }

        private static String normalizeRobotName(String myPrefix) {
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < myPrefix.length(); i++) {
                char c = myPrefix.charAt(i);
                if (!Character.isWhitespace(c) && c != '_') {
                    sb.append(Character.toLowerCase(c));
                }
            }
            return sb.toString();
        }

        @Override
        public boolean prefixMatches(@NotNull String name) {
            name = normalizeRobotName(name);
            return name.contains(normalizedPrefix);
        }

        @Override
        public @NotNull PrefixMatcher cloneWithPrefix(@NotNull String prefix) {
            return new LSPPrefixMatcher(prefix);
        }

        @Override
        public boolean isStartMatch(String name) {
            name = normalizeRobotName(name);
            return name.startsWith(normalizedPrefix);
        }
    }

    @Override
    public @Nullable AutoCompletionDecision handleAutoCompletionPossibility(@NotNull AutoCompletionContext context) {
        return super.handleAutoCompletionPossibility(context);
    }

    @Override
    public void fillCompletionVariants(@NotNull CompletionParameters parameters, @NotNull CompletionResultSet result) {
        final Editor editor = parameters.getEditor();
        final int offset = parameters.getOffset();
        final EditorLanguageServerConnection editorLanguageServerConnection = EditorLanguageServerConnection.getFromUserData(editor);
        if (editorLanguageServerConnection != null) {
            try {
                final String lineToCursor = EditorUtils.getLineToCursor(editor.getDocument(), offset);

                ProgressIndicator progressIndicator = ProgressIndicatorProvider.getGlobalProgressIndicator();
                if (progressIndicator == null) {
                    progressIndicator = new EmptyProgressIndicator();
                }
                ApplicationUtil.runWithCheckCanceled(() -> {
                    CompletableFuture<Either<List<CompletionItem>, CompletionList>> completion = editorLanguageServerConnection.completion(offset);
                    CompletableFuture<Either<List<CompletionItem>, CompletionList>> oldCompletion = currentCompletion.getAndSet(completion);
                    if (oldCompletion != null) {
                        // i.e.: Whenever we start a completion cancel the previous one (which is very common
                        // when completing as we type).
                        try {
                            oldCompletion.cancel(true);
                        } catch (ProcessCanceledException | CompletionException | CancellationException e) {
                            // ignore
                        }
                    }

                    if (completion == null) {
                        return null;
                    }
                    Either<List<CompletionItem>, CompletionList> res = null;
                    long timeout = Timeouts.getCompletionTimeout();
                    long timeoutAt = System.currentTimeMillis() + (timeout * 1000);
                    while (true) {
                        try {
                            res = completion.get(50, TimeUnit.MILLISECONDS);
                            break; // Ok, completion gotten
                        } catch (TimeoutException e) {
                            // ignore internal timeout
                        }
                        if (System.currentTimeMillis() > timeoutAt) {
                            // Timed out (cancel the completion on the server).
                            completion.cancel(true);
                            return null;
                        }
                    }

                    if (res == null) {
                        return null;
                    }

                    String prefix = LSPPrefixMatcher.getPrefix(lineToCursor);
                    @NotNull CompletionResultSet completionResult = result.withPrefixMatcher(new LSPPrefixMatcher(prefix));
                    completionResult.startBatch();
                    try {
                        if (res.getLeft() != null) {
                            for (CompletionItem item : res.getLeft()) {
                                LookupElement lookupElement = createLookupItem(item, offset);
                                completionResult.addElement(lookupElement);
                            }
                        } else if (res.getRight() != null) {
                            for (CompletionItem item : res.getRight().getItems()) {
                                LookupElement lookupElement = createLookupItem(item, offset);
                                completionResult.addElement(lookupElement);
                            }
                        }
                    } finally {
                        completionResult.endBatch();
                    }

                    return null;
                }, progressIndicator);
            } catch (ProcessCanceledException | CompletionException | CancellationException |
                     InterruptedException ignored) {
                // Cancelled (InterruptedException is thrown when completion.cancel(true) is called from another thread).
            } catch (Exception e) {
                LOG.error("Unable to get completions", e);
            }
        }
    }

    private @NotNull LookupElement createLookupItem(final CompletionItem item, final int requestedAtOffset) {
        final CompletionItemKind kind = item.getKind();
        final String label = item.getLabel();
        final Icon icon = LanguageServerIcons.getCompletionIcon(kind);
        final String lookupString = label;

        LookupElement ret = new LanguageServerLookupElement(lookupString, label, kind, icon, item, requestedAtOffset);

        ret.putUserData(CodeCompletionHandlerBase.DIRECT_INSERTION, true);
        return ret;
    }

    public static class LanguageServerLookupElement extends LookupElement {

        private final String lookupString;
        private final String label;
        private final CompletionItemKind kind;
        private final Icon icon;
        private final CompletionItem item;
        private final int requestedAtOffset;

        public LanguageServerLookupElement(String lookupString, String label, CompletionItemKind kind, Icon icon, CompletionItem item, int requestedAtOffset) {
            this.lookupString = lookupString;
            this.label = label;
            this.kind = kind;
            this.icon = icon;
            this.item = item;
            this.requestedAtOffset = requestedAtOffset;
        }

        @Override
        public @NotNull String getLookupString() {
            return lookupString;
        }

        @Override
        public boolean requiresCommittedDocuments() {
            return false;
        }

        @Override
        public void renderElement(LookupElementPresentation presentation) {
            presentation.setItemText(label);
            presentation.setItemTextBold(kind == CompletionItemKind.Keyword);
            presentation.setIcon(icon);
        }

        @Override
        public boolean isCaseSensitive() {
            return false;
        }

        public AutoCompletionPolicy getAutoCompletionPolicy() {
            return AUTO_COMPLETION_POLICY;
        }

        @Override
        public void handleInsert(@NotNull InsertionContext context) {
            EditorUtils.runWriteAction(() -> {
                doHandleInsert(context);
            });
        }

        private void doHandleInsert(@NotNull InsertionContext context) {
            Either<TextEdit, InsertReplaceEdit> either = item.getTextEdit();
            if (!either.isLeft()) {
                throw new RuntimeException("Expected only TextEdit, not InsertReplaceEdit.");
            }
            TextEdit textEdit = either.getLeft();
            Document document = context.getDocument();
            int tailOffset = context.getTailOffset();
            Position startPos = textEdit.getRange().getStart();

            int lineStartOffset = document.getLineStartOffset(startPos.getLine());
            String lineTextToCursor = "";
            if (lineStartOffset < tailOffset) {
                lineTextToCursor = document.getText(new TextRange(lineStartOffset, tailOffset));
            }

            if (requestedAtOffset != tailOffset) {
                document.deleteString(requestedAtOffset, tailOffset);
            }

            ArrayList<TextEdit> lst = new ArrayList<>();
            String originalText = textEdit.getNewText();
            int i;
            if ((i = originalText.indexOf('\n')) != -1) {
                // i.e.: properly indent the other lines
                String indentationFromLine = StringUtils.getIndentationFromLine(lineTextToCursor);
                List<String> lines = StringUtils.splitInLines(originalText);
                Iterator<String> it = lines.iterator();
                FastStringBuffer buf = new FastStringBuffer(it.next(), indentationFromLine.length() * 10); // First is added as is.
                while (it.hasNext()) {
                    buf.append(indentationFromLine);
                    buf.append(it.next());
                }
                originalText = buf.toString();
            }
            if (item.getInsertTextFormat() == InsertTextFormat.Snippet) {
                textEdit.setNewText(removePlaceholders(originalText));
            }
            lst.add(textEdit);
            List<TextEdit> additionalTextEdits = item.getAdditionalTextEdits();
            if (additionalTextEdits != null) {
                lst.addAll(additionalTextEdits);
            }
            try {
                EditorUtils.applyTextEdits(document, lst);
                context.commitDocument();
            } catch (BadLocationException e) {
                LOG.error(e);
            }

            // Calculate the new cursor offset.
            Position offsetPos = new Position(startPos.getLine(), startPos.getCharacter());
            if (additionalTextEdits != null) {
                for (TextEdit t : additionalTextEdits) {
                    if (t.getRange().getStart().getLine() < offsetPos.getLine()) {
                        int newLines = StringUtil.countNewLines(t.getNewText());
                        offsetPos.setLine(offsetPos.getLine() + newLines);
                    }
                }
            }
            int offset = EditorUtils.LSPPosToOffset(document, offsetPos) + textEdit.getNewText().length();
            context.getEditor().getCaretModel().moveToOffset(offset);
            if (item.getInsertTextFormat() == InsertTextFormat.Snippet) {
                prepareAndRunSnippet(context, originalText);
            }
        }

        private static final Pattern SNIPPET_PLACEHOLDER_REGEX = Pattern.compile("(\\$\\{\\d+:?([^{^}]*)}|\\$\\d+)");

        private static String removePlaceholders(String text) {
            return SNIPPET_PLACEHOLDER_REGEX.matcher(text).replaceAll("").replace("\\$", "$");
        }

        private void prepareAndRunSnippet(@NotNull InsertionContext context, @NotNull String insertText) {
            Editor editor = context.getEditor();
            Project project = editor.getProject();
            if (project == null) {
                return;
            }
            List<SnippetVariable> variables = new ArrayList<>();
            // Extracts variables using placeholder REGEX pattern.
            Matcher varMatcher = SNIPPET_PLACEHOLDER_REGEX.matcher(insertText);
            while (varMatcher.find()) {
                variables.add(new SnippetVariable(varMatcher.group(), varMatcher.start(), varMatcher.end()));
            }
            if (variables.isEmpty()) {
                return;
            }

            variables.sort(Comparator.comparingInt(o -> o.startIndex));
            String finalInsertText = insertText;
            for (SnippetVariable var : variables) {
                finalInsertText = finalInsertText.replace(var.lspSnippetText, "XXX_REPLACE_XXX_ROBOT_LSP_XXX");
            }

            String[] splitInsertText = finalInsertText.split("XXX_REPLACE_XXX_ROBOT_LSP_XXX");
            finalInsertText = String.join("", splitInsertText);

            TemplateImpl template = (TemplateImpl) TemplateManager.getInstance(project).createTemplate(finalInsertText,
                    "groupLSP");
            template.parseSegments();

            // prevent "smart" indent of next line...
            template.setToIndent(false);

            int varIndex = 0;
            for (SnippetVariable var : variables) {
                var.variableValue = var.variableValue.replace("\\$", "$");
                String text = splitInsertText[varIndex];
                template.addTextSegment(text);
                String name = varIndex + "_" + var.variableValue;
                template.addVariable(name, new TextExpression(var.variableValue),
                        new TextExpression(var.variableValue), true, false);
                varIndex++;
            }
            // If the snippet text ends with a placeholder, there will be no string segment left to append after the last
            // variable.
            if (splitInsertText.length != variables.size()) {
                template.addTextSegment(splitInsertText[splitInsertText.length - 1]);
            }
            template.setInline(true);
            if (variables.size() > 0) {
                EditorModificationUtil.moveCaretRelatively(editor, -template.getTemplateText().length());
            }
            TemplateManager.getInstance(project).startTemplate(editor, template);
        }
    }
}
