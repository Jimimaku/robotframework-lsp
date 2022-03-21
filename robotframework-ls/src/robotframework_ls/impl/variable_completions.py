from robocorp_ls_core.cache import instance_cache
from robotframework_ls.impl.protocols import (
    ICompletionContext,
    IRobotDocument,
    IVariablesCollector,
    IVariableFound,
    IRobotToken,
    TokenInfo,
)
from robocorp_ls_core.robotframework_log import get_logger
from robocorp_ls_core.protocols import check_implements, IDocumentSelection
from typing import Optional, List
from robotframework_ls.impl.text_utilities import normalize_robot_name
from robocorp_ls_core.lsp import CompletionItemTypedDict
import itertools

log = get_logger(__name__)


class _VariableFoundFromToken(object):
    def __init__(
        self, completion_context, variable_token, variable_value, variable_name=None
    ):
        self.completion_context = completion_context
        self.variable_token = variable_token

        if variable_name is None:
            variable_name = str(variable_token)
        self.variable_name = variable_name
        if isinstance(variable_value, (list, tuple, set)):
            if len(variable_value) == 1:
                self.variable_value = str(next(iter(variable_value)))
            else:
                self.variable_value = str(variable_value)
        else:
            self.variable_value = str(variable_value)

    @property  # type: ignore
    @instance_cache
    def source(self):
        from robocorp_ls_core import uris

        return uris.to_fs_path(self.completion_context.doc.uri)

    @property
    def lineno(self):
        return self.variable_token.lineno - 1  # Make 0-based

    @property
    def end_lineno(self):
        return self.variable_token.lineno - 1  # Make 0-based

    @property
    def col_offset(self):
        return self.variable_token.col_offset

    @property
    def end_col_offset(self):
        return self.variable_token.end_col_offset

    def __typecheckself__(self) -> None:
        _: IVariableFound = check_implements(self)


class _VariableFoundFromPythonAst(object):
    def __init__(
        self,
        path: str,
        lineno: int,
        col: int,
        end_lineno: int,
        end_col: int,
        variable_value: str,
        variable_name: str,
    ):
        self.lineno = lineno
        self.col_offset = col
        self.end_lineno = end_lineno
        self.end_col_offset = end_col

        self.completion_context: Optional[ICompletionContext] = None
        self._path = path
        self.variable_name = variable_name
        self.variable_value = variable_value

    @property
    def source(self):
        return self._path

    def __typecheckself__(self) -> None:
        _: IVariableFound = check_implements(self)


class _VariableFoundFromSettings(object):
    def __init__(self, variable_name, variable_value, source="", lineno=0):
        self.completion_context = None
        self.variable_name = variable_name
        self.variable_value = str(variable_value)
        self._source = source
        self._lineno = lineno

    @property
    def source(self):
        return self._source

    @property
    def lineno(self):
        return self._lineno

    @property
    def end_lineno(self):
        return self._lineno

    @property
    def col_offset(self):
        return 0

    @property
    def end_col_offset(self):
        return 0

    def __typecheckself__(self) -> None:
        _: IVariableFound = check_implements(self)


class _VariableFoundFromBuiltins(_VariableFoundFromSettings):
    pass


class _VariableFoundFromYaml(_VariableFoundFromSettings):
    pass


class _Collector(object):
    def __init__(self, selection: IDocumentSelection, token: IRobotToken, matcher):
        self.matcher = matcher
        self.completion_items: List[CompletionItemTypedDict] = []
        self.selection = selection
        self.token = token

    def _create_completion_item_from_variable(
        self,
        variable_found: IVariableFound,
        selection: IDocumentSelection,
        token: IRobotToken,
    ) -> CompletionItemTypedDict:
        from robocorp_ls_core.lsp import (
            CompletionItem,
            InsertTextFormat,
            Position,
            Range,
            TextEdit,
        )
        from robocorp_ls_core.lsp import CompletionItemKind

        label = variable_found.variable_name
        text = label
        text = text.replace("$", "\\$")

        text_edit = TextEdit(
            Range(
                start=Position(selection.line, token.col_offset),
                end=Position(selection.line, token.end_col_offset),
            ),
            text,
        )

        # text_edit = None
        return CompletionItem(
            variable_found.variable_name,
            kind=CompletionItemKind.Variable,
            text_edit=text_edit,
            insertText=label,
            documentation=variable_found.variable_value,
            insertTextFormat=InsertTextFormat.Snippet,
        ).to_dict()

    def accepts(self, variable_name: str) -> bool:
        return self.matcher.accepts(variable_name)

    def on_variable(self, variable_found: IVariableFound):
        self.completion_items.append(
            self._create_completion_item_from_variable(
                variable_found, self.selection, self.token
            )
        )

    def __typecheckself__(self) -> None:
        _: IVariablesCollector = check_implements(self)


def _collect_completions_from_ast(
    ast, completion_context: ICompletionContext, collector: IVariablesCollector
):
    from robotframework_ls.impl import ast_utils

    completion_context.check_cancelled()
    from robot.api import Token

    for variable_node_info in completion_context.get_all_variables():
        variable_node = variable_node_info.node
        token = variable_node.get_token(Token.VARIABLE)
        if token is None:
            continue
        name = token.value
        if not name:
            continue
        name = name.strip()
        if not name:
            continue
        if name.endswith("="):
            name = name[:-1].rstrip()

        if name.startswith(("&", "@")):
            # Allow referencing dict(&)/list(@) variables as regular ($) variables
            dict_or_list_var = "$" + name[1:]
            if collector.accepts(dict_or_list_var):
                variable_found = _VariableFoundFromToken(
                    completion_context,
                    token,
                    variable_node.value,
                    variable_name=dict_or_list_var,
                )
                collector.on_variable(variable_found)
        if collector.accepts(name):
            variable_found = _VariableFoundFromToken(
                completion_context, token, variable_node.value, variable_name=name
            )
            collector.on_variable(variable_found)

    accept_sets_in = {
        normalize_robot_name("Set Task Variable"),
        normalize_robot_name("Set Test Variable"),
        normalize_robot_name("Set Suite Variable"),
        normalize_robot_name("Set Global Variable"),
    }
    ast = completion_context.get_ast()
    for keyword_usage in ast_utils.iter_keyword_usage_tokens(
        ast, collect_args_as_keywords=True
    ):
        if normalize_robot_name(keyword_usage.name) in accept_sets_in:
            var_name_tok = None
            var_value_tok = None
            for tok in keyword_usage.node.tokens:
                if tok.type == Token.ARGUMENT:
                    if var_name_tok is None:
                        var_name_tok = tok
                    else:
                        var_value_tok = tok
                        break

            if var_name_tok is not None:
                if collector.accepts(var_name_tok.value):
                    variable_value = ""
                    if var_value_tok is not None:
                        variable_value = var_value_tok.value

                    variable_found = _VariableFoundFromToken(
                        completion_context,
                        var_name_tok,
                        variable_value=variable_value,
                    )
                    collector.on_variable(variable_found)


def _collect_current_doc_variables(
    completion_context: ICompletionContext, collector: IVariablesCollector
):
    """
    :param CompletionContext completion_context:
    """
    # Get keywords defined in the file itself

    ast = completion_context.get_ast()
    _collect_completions_from_ast(ast, completion_context, collector)


def _collect_resource_imports_variables(
    completion_context: ICompletionContext, collector: IVariablesCollector
):
    resource_doc: Optional[IRobotDocument]
    for _node, resource_doc in completion_context.get_resource_imports_as_docs():
        if resource_doc is None:
            continue
        new_ctx = completion_context.create_copy(resource_doc)
        _collect_variables_from_document_context(new_ctx, collector)


def _collect_variables_from_variable_import_doc(
    variable_import_doc: IRobotDocument, collector: IVariablesCollector
):
    try:
        if variable_import_doc.path.lower().endswith(".py"):
            python_ast = variable_import_doc.get_python_ast()
            if python_ast is not None:
                import ast as ast_module

                for node in python_ast.body:
                    if isinstance(node, ast_module.Assign):
                        for target in node.targets:
                            if isinstance(target, ast_module.Name):
                                varname = "${%s}" % (target.id,)
                                if collector.accepts(varname):
                                    value = ""
                                    try:
                                        # Only available for Python 3.8 onwards...
                                        end_lineno = getattr(
                                            node.value, "end_lineno", None
                                        )
                                        if end_lineno is None:
                                            end_lineno = node.value.lineno

                                        # Only available for Python 3.8 onwards...
                                        end_col_offset = getattr(
                                            node.value, "end_col_offset", None
                                        )
                                        if end_col_offset is None:
                                            end_col_offset = 99999999
                                        value = variable_import_doc.get_range(
                                            node.value.lineno - 1,
                                            node.value.col_offset,
                                            end_lineno - 1,
                                            end_col_offset,
                                        )
                                    except:
                                        log.exception()

                                    variable_found = _VariableFoundFromPythonAst(
                                        variable_import_doc.path,
                                        target.lineno - 1,
                                        target.col_offset,
                                        target.lineno - 1,
                                        target.col_offset + len(target.id),
                                        value,
                                        variable_name=varname,
                                    )
                                    collector.on_variable(variable_found)

        elif variable_import_doc.path.lower().endswith((".yaml", ".yml")):
            dct_contents = variable_import_doc.get_yaml_contents()
            if isinstance(dct_contents, dict):
                if dct_contents:
                    try_to_compute_line = (
                        variable_import_doc.source.count("\n") * len(dct_contents)
                    ) <= 200
                    # Our (lame) algorithm to find a key will need to iterate
                    # over all lines for all entries, so, do it only for
                    # small docs (consider a better algorithm in the future)...
                    for initial_key, val in dct_contents.items():
                        key = "${%s}" % (initial_key,)

                        lineno = 0
                        if try_to_compute_line:
                            try:
                                # We don't have the real lineno during parsing,
                                # so, make a little hack to get something which
                                # may be close...
                                (
                                    lineno,
                                    _,
                                ) = variable_import_doc.get_last_line_col_with_contents(
                                    initial_key
                                )
                            except RuntimeError:
                                pass

                        if collector.accepts(key):
                            collector.on_variable(
                                _VariableFoundFromYaml(
                                    key,
                                    str(val),
                                    source=variable_import_doc.path,
                                    lineno=lineno,
                                )
                            )

    except:
        log.exception()


def _iter_resource_docs(completion_context: ICompletionContext, dependency_graph):
    visited = set()
    for resource_doc in itertools.chain(
        (d[1] for d in dependency_graph.iter_all_resource_imports_with_docs()),
        iter(completion_context.get_resource_inits_as_docs()),
    ):
        if resource_doc is not None:
            if resource_doc.uri not in visited:
                visited.add(resource_doc.uri)
                yield resource_doc


def _collect_variables_from_document_context(
    completion_context: ICompletionContext,
    collector: IVariablesCollector,
    only_current_doc=False,
):
    completion_context.check_cancelled()
    _collect_current_doc_variables(completion_context, collector)

    if not only_current_doc:
        dependency_graph = completion_context.collect_dependency_graph()

        for resource_doc in _iter_resource_docs(completion_context, dependency_graph):
            if resource_doc is not None:
                new_ctx = completion_context.create_copy(resource_doc)
                _collect_current_doc_variables(new_ctx, collector)

        for node, variable_doc in dependency_graph.iter_all_variable_imports_as_docs():
            if variable_doc is None:
                # Note that 'None' documents will only be given for the
                # initial context (so, it's ok to use `completion_context`
                # in this case).
                from robot.api import Token

                node_name_tok = node.get_token(Token.NAME)
                if node_name_tok is not None:

                    (
                        _value,
                        token_errors,
                    ) = completion_context.token_value_and_unresolved_resolving_variables(
                        node_name_tok
                    )

                    if token_errors:
                        for token_error in token_errors:
                            collector.on_unresolved_variable_import(
                                completion_context,
                                node.name,
                                token_error.lineno,
                                token_error.lineno,
                                token_error.col_offset,
                                token_error.end_col_offset,
                                f"\nUnable to statically resolve variable: {token_error.value}.\nPlease set the `{token_error.value[2:-1]}` value in `robot.variables`.",
                            )

                    else:
                        collector.on_unresolved_variable_import(
                            completion_context,
                            node.name,
                            node_name_tok.lineno,
                            node_name_tok.lineno,
                            node_name_tok.col_offset,
                            node_name_tok.end_col_offset,
                            None,
                        )
                else:
                    collector.on_unresolved_variable_import(
                        completion_context,
                        node.name,
                        node.lineno,
                        node.end_lineno,
                        node.col_offset,
                        node.end_col_offset,
                        None,
                    )
                continue
            _collect_variables_from_variable_import_doc(variable_doc, collector)


def _collect_arguments(
    completion_context: ICompletionContext,
    node,
    collector: IVariablesCollector,
):
    from robotframework_ls.impl import ast_utils

    for arg_token in ast_utils.iter_keyword_arguments_as_tokens(
        node, tokenize_keyword_name=True
    ):
        name = str(arg_token)
        if collector.accepts(name):
            variable_found = _VariableFoundFromToken(
                completion_context, arg_token, "", variable_name=name
            )
            collector.on_variable(variable_found)


def _convert_name_to_var(variable_name):
    if not variable_name.strip().endswith("}"):
        variable_name = "${%s}" % (variable_name,)
    return variable_name


def _collect_from_settings(
    completion_context: ICompletionContext, collector: IVariablesCollector
):
    from robotframework_ls.impl.robot_lsp_constants import OPTION_ROBOT_VARIABLES

    config = completion_context.config
    if config is not None:
        robot_variables = config.get_setting(OPTION_ROBOT_VARIABLES, dict, {})
        for key, val in robot_variables.items():
            key = _convert_name_to_var(key)
            if collector.accepts(key):
                collector.on_variable(_VariableFoundFromSettings(key, val))


def _collect_from_builtins(
    completion_context: ICompletionContext, collector: IVariablesCollector
):
    from robotframework_ls.impl.robot_constants import BUILTIN_VARIABLES

    for key, val in BUILTIN_VARIABLES:
        key = _convert_name_to_var(key)
        if collector.accepts(key):
            collector.on_variable(_VariableFoundFromBuiltins(key, val))


def collect_variables(
    completion_context: ICompletionContext,
    collector: IVariablesCollector,
    only_current_doc=False,
):
    token_info = completion_context.get_current_token()
    if token_info is not None:
        collect_local_variables(completion_context, collector, token_info)

    collect_global_variables(completion_context, collector, only_current_doc)


def collect_global_variables(
    completion_context: ICompletionContext,
    collector: IVariablesCollector,
    only_current_doc=False,
):
    _collect_variables_from_document_context(
        completion_context, collector, only_current_doc=only_current_doc
    )

    if not only_current_doc:
        _collect_from_settings(completion_context, collector)
        _collect_from_builtins(completion_context, collector)


def collect_local_variables(
    completion_context: ICompletionContext,
    collector: IVariablesCollector,
    token_info: TokenInfo,
):
    from robotframework_ls.impl import ast_utils

    if token_info.stack:
        for stack_node in reversed(token_info.stack):
            if stack_node.__class__.__name__ in ("Keyword", "TestCase"):
                break
        else:
            stack_node = token_info.stack[0]
    else:
        stack_node = completion_context.get_ast_current_section()

    for assign_node_info in itertools.chain(
        ast_utils.iter_variable_assigns(stack_node),
        ast_utils.iter_for_assigns(stack_node),
        ast_utils.iter_except_as_assigns(stack_node),
    ):
        completion_context.check_cancelled()
        if collector.accepts(assign_node_info.token.value):
            rep = " ".join(tok.value for tok in assign_node_info.node.tokens)
            variable_found = _VariableFoundFromToken(
                completion_context, assign_node_info.token, rep
            )
            collector.on_variable(variable_found)

    _collect_arguments(completion_context, stack_node, collector)


def complete(completion_context: ICompletionContext):
    from robotframework_ls.impl.string_matcher import RobotStringMatcher

    token_info = completion_context.get_current_variable()
    if token_info is not None:
        token = token_info.token
        value = token.value
        if value.endswith("}"):
            value = value[:-1]
        collector = _Collector(completion_context.sel, token, RobotStringMatcher(value))
        collect_variables(completion_context, collector)
        return collector.completion_items
    return []
