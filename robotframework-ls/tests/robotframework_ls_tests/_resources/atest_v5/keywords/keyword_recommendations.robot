*** Settings ***
Resource          resources/recommendation_resource_1.robot
Resource          resources/recommendation_resource_2.robot
Library           resources/RecLibrary1.py
Library           resources/RecLibrary2.py    WITH NAME    Rec Library 2 With Custom Name

*** Variables ***
${INDENT}    ${SPACE * 4}

*** Test Cases ***
Keyword From Library Not Imported
    [Documentation]    FAIL
    ...    No keyword with name 'RecLibrary3.Keyword Only In Library 3' found. Did you mean:
    ...    ${INDENT}RecLibrary1.Keyword Only In Library 1
    RecLibrary3.Keyword Only In Library 3
#!  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ Undefined keyword: RecLibrary3.Keyword Only In Library 3.

Implicit Keyword With Typo
    [Documentation]    FAIL
    ...    No keyword with name 'Recoord' found. Did you mean:
    ...    ${INDENT}RecLibrary1.Record
    Recoord    log message
#!  ^^^^^^^ Undefined keyword: Recoord.

Explicit Keyword With Typo
    [Documentation]    FAIL
    ...    No keyword with name 'RecLibrarry1.Record' found. Did you mean:
    ...    ${INDENT}RecLibrary1.Record
    RecLibrarry1.Record    log message
#!  ^^^^^^^^^^^^^^^^^^^ Undefined keyword: RecLibrarry1.Record.

Explicit Keyword Similar To Keyword In Imported Library
    [Documentation]    FAIL
    ...    No keyword with name 'RecLibrary1.Keywword Only In Library 1' found. Did you mean:
    ...    ${INDENT}RecLibrary1.Keyword Only In Library 1
    RecLibrary1.Keywword Only In Library 1
#!  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ Undefined keyword: RecLibrary1.Keywword Only In Library 1.

Implicit Keyword Similar To Keyword In Imported Library
    [Documentation]    FAIL
    ...    No keyword with name 'Keywword Only In Library 1' found. Did you mean:
    ...    ${INDENT}RecLibrary1.Keyword Only In Library 1
    ...    ${INDENT}Rec Library 2 With Custom Name.Keyword Only In Library 2
    Keywword Only In Library 1
#!  ^^^^^^^^^^^^^^^^^^^^^^^^^^ Undefined keyword: Keywword Only In Library 1.

Explicit Keyword Similar To Keyword In Imported Resource
    [Documentation]    FAIL
    ...    No keyword with name 'recommendation_resource_1.Keywword Only In Resource 1' found. Did you mean:
    ...    ${INDENT}recommendation_resource_1.Keyword Only In Resource 1
    ...    ${INDENT}recommendation_resource_2.Keyword Only In Resource 2
    ...    ${INDENT}recommendation_resource_1.Keyword In Both Resources
    ...    ${INDENT}recommendation_resource_2.Keyword In Both Resources
    recommendation_resource_1.Keywword Only In Resource 1
#!  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ Undefined keyword: recommendation_resource_1.Keywword Only In Resource 1.

Implicit Keyword Similar To Keyword In Imported Resource
    [Documentation]    FAIL
    ...    No keyword with name 'Keywword Only In Resource 1' found. Did you mean:
    ...    ${INDENT}recommendation_resource_1.Keyword Only In Resource 1
    ...    ${INDENT}recommendation_resource_2.Keyword Only In Resource 2
    Keywword Only In Resource 1
#!  ^^^^^^^^^^^^^^^^^^^^^^^^^^^ Undefined keyword: Keywword Only In Resource 1.

Implicit Long Alphanumeric Garbage Keyword
    [Documentation]    FAIL    No keyword with name 'fhj329gh9ufhds98f3972hufd9fh839832fh9ud8h8' found.
    fhj329gh9ufhds98f3972hufd9fh839832fh9ud8h8
#!  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ Undefined keyword: fhj329gh9ufhds98f3972hufd9fh839832fh9ud8h8.

Explicit Long Alphanumeric Garbage Keyword
    [Documentation]    FAIL    No keyword with name 'fhj329gh9ufhds98.f3972hufd9fh839832fh9ud8h8' found.
    fhj329gh9ufhds98.f3972hufd9fh839832fh9ud8h8
#!  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ Undefined keyword: fhj329gh9ufhds98.f3972hufd9fh839832fh9ud8h8.

Implicit Special Character Garbage Keyword
    [Documentation]    FAIL    No keyword with name '*&(&^%&%$#%#@###!@!#@$$%#%&^<">:>?:""{+' found.
    *&(&^%&%$#%#@###!@!#@$$%#%&^<">:>?:""{+
#!  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ Undefined keyword: *&(&^%&%$#%#@###!@!#@$$%#%&^<">:>?:""{+.

Explicit Special Character Garbage Keyword
    [Documentation]    FAIL    No keyword with name '*&(&^%&%$#.%#@###!@!#@$$%#%&^<">:>?:""{+' found.
    *&(&^%&%$#.%#@###!@!#@$$%#%&^<">:>?:""{+
#!  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ Undefined keyword: *&(&^%&%$#.%#@###!@!#@$$%#%&^<">:>?:""{+.

Implicit Keyword Similar To User Keyword
    [Documentation]    FAIL    No keyword with name 'A Uuser Keyword' found. Did you mean:
    ...    ${INDENT}A User Keyword
    A Uuser Keyword
#!  ^^^^^^^^^^^^^^^ Undefined keyword: A Uuser Keyword.

Wrapped By Run Keyword Implicit Missing
    [Documentation]    FAIL    No keyword with name 'missing keyword' found.
    Run Keyword    missing keyword
#!                 ^^^^^^^^^^^^^^^ Undefined keyword: missing keyword.

Wrapped By Run Keyword Implicit Missing Similar To Both Libraries
    [Documentation]    FAIL
    ...    No keyword with name 'kkeyword in both libraries' found. Did you mean:
    ...    ${INDENT}Rec Library 2 With Custom Name.Keyword In Both Libraries
    ...    ${INDENT}RecLibrary1.Keyword In Both Libraries
    Run Keyword    kkeyword in both libraries
#!                 ^^^^^^^^^^^^^^^^^^^^^^^^^^ Undefined keyword: kkeyword in both libraries.

Wrapped By Run Keyword Explicit Missing Similar To Both Libraries
    [Documentation]    FAIL
    ...    No keyword with name 'RecLibrary1.kkeyword in both libraries' found. Did you mean:
    ...    ${INDENT}RecLibrary1.Keyword In Both Libraries
    Run Keyword    RecLibrary1.kkeyword in both libraries
#!                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ Undefined keyword: RecLibrary1.kkeyword in both libraries.

Wrapped By Run Keyword Explicit Missing
    [Documentation]    FAIL    No keyword with name 'RecLibrary1.missing keyword' found.
    Run Keyword    RecLibrary1.missing keyword
#!                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^ Undefined keyword: RecLibrary1.missing keyword.

Wrapped By Run Keyword And Ignore Error
    ${status}    ${error} =    Run Keyword And Ignore Error    missing keyword
#!                                                             ^^^^^^^^^^^^^^^ Undefined keyword: missing keyword.
    Should Be Equal    ${status}    FAIL
    Should Be Equal    ${error}    No keyword with name 'missing keyword' found.

Wrapped By Run Keyword Whitespace
    [Documentation]    FAIL    No keyword with name ' ' found.
    Run Keyword    ${SPACE}

Misspelled Keyword Capitalized
    [Documentation]    FAIL
    ...    No keyword with name 'Do Atcion' found. Did you mean:
    ...    ${INDENT}RecLibrary1.Do Action
    Do Atcion
#!  ^^^^^^^^^ Undefined keyword: Do Atcion.

Misspelled Keyword Lowercase
    [Documentation]    FAIL
    ...    No keyword with name 'do atcion' found. Did you mean:
    ...    ${INDENT}RecLibrary1.Do Action
    do atcion
#!  ^^^^^^^^^ Undefined keyword: do atcion.

Misspelled Keyword All Caps
    [Documentation]    FAIL
    ...    No keyword with name 'DO ATCION' found. Did you mean:
    ...    ${INDENT}RecLibrary1.Do Action
    DO ATCION
#!  ^^^^^^^^^ Undefined keyword: DO ATCION.

Misspelled Keyword Underscore
    [Documentation]    FAIL
    ...    No keyword with name 'do_atcion' found. Did you mean:
    ...    ${INDENT}RecLibrary1.Do Action
    do_atcion
#!  ^^^^^^^^^ Undefined keyword: do_atcion.

Misspelled Keyword Explicit
    [Documentation]    FAIL
    ...    No keyword with name 'RecLibrary1.DoAtcion' found. Did you mean:
    ...    ${INDENT}RecLibrary1.Do Action
    ...    ${INDENT}RecLibrary1.Action
    RecLibrary1.DoAtcion
#!  ^^^^^^^^^^^^^^^^^^^^ Undefined keyword: RecLibrary1.DoAtcion.

Misspelled Keyword Spacing
    [Documentation]    FAIL
    ...    No keyword with name 'd o a t c i o n' found. Did you mean:
    ...    ${INDENT}RecLibrary1.Do Action
    d o a t c i o n
#!  ^^^^^^^^^^^^^^^ Undefined keyword: d o a t c i o n.

Misspelled Keyword No Whitespace
    [Documentation]    FAIL
    ...    No keyword with name 'DoAtcion' found. Did you mean:
    ...    ${INDENT}RecLibrary1.Do Action
    DoAtcion
#!  ^^^^^^^^ Undefined keyword: DoAtcion.

Keyword With Period
    [Documentation]    FAIL
    ...    No keyword with name 'Kye.word with_periods' found. Did you mean:
    ...    ${INDENT}Key.word.with Periods.
    Kye.word with_periods
#!  ^^^^^^^^^^^^^^^^^^^^^ Undefined keyword: Kye.word with_periods.

Keyword With Periods
    [Documentation]    FAIL
    ...    No keyword with name 'Kye.word.with_periods' found. Did you mean:
    ...    ${INDENT}Key.word.with Periods.
    Kye.word.with_periods
#!  ^^^^^^^^^^^^^^^^^^^^^ Undefined keyword: Kye.word.with_periods.

Similar User Keywords
    [Documentation]    FAIL
    ...    No keyword with name 'Similar User Keyword 4' found. Did you mean:
    ...    ${INDENT}Similar User Keyword 3
    ...    ${INDENT}Similar User Keyword 2
    ...    ${INDENT}Similar User Keyword 1
    Similar User Keyword 4
#!  ^^^^^^^^^^^^^^^^^^^^^^ Undefined keyword: Similar User Keyword 4.

Similar Keywords In Resources And Libraries
    [Documentation]    FAIL
    ...    No keyword with name 'Similar Kw' found. Did you mean:
    ...    ${INDENT}Similar Kw 5
    ...    ${INDENT}Rec Library 2 With Custom Name.Similar Kw 4
    ...    ${INDENT}RecLibrary1.Similar Kw 3
    ...    ${INDENT}recommendation_resource_2.Similar Kw 2
    ...    ${INDENT}recommendation_resource_1.Similar Kw 1
    Similar Kw
#!  ^^^^^^^^^^ Undefined keyword: Similar Kw.

Non-similar Embedded User Keyword
    [Documentation]    FAIL    No keyword with name 'Unique misspelled kkw blah' found.
    Unique misspelled kkw blah

Embedded Similar User Keywords
    [Documentation]    FAIL    No keyword with name 'Embbedded User joe Argument password Keyword 3' found.
    Embbedded User joe Argument password Keyword 3
#!  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ Undefined keyword: Embbedded User joe Argument password Keyword 3.

Existing Non-ASCII Keyword
    [Documentation]    FAIL
    ...    No keyword with name 'hyvää öytä' found. Did you mean:
    ...    ${INDENT}Hyvää Yötä
    hyvää öytä
#!  ^^^^^^^^^^ Undefined keyword: hyvää öytä.

Wrong Library Name
    [Documentation]    FAIL    No keyword with name 'NoSuchLib.Nothing' found.
    NoSuchLib.Nothing
#!  ^^^^^^^^^^^^^^^^^ Undefined keyword: NoSuchLib.Nothing.

Wrong Library Name 2
    [Documentation]    FAIL    No keyword with name 'NoSuchLib.Action' found.
    NoSuchLib.Action
#!  ^^^^^^^^^^^^^^^^ Undefined keyword: NoSuchLib.Action.

BuiltIn Similar To Other BuiltIns
    [Documentation]    FAIL
    ...    No keyword with name 'Atcion And Ignore Problems' found. Did you mean:
    ...    ${INDENT}RecLibrary1.Action And Ignore Problems
    Atcion And Ignore Problems
#!  ^^^^^^^^^^^^^^^^^^^^^^^^^^ Undefined keyword: Atcion And Ignore Problems.

Substring of Long Keyword
    [Documentation]    FAIL    No keyword with name 'Really Long Keyword' found.
    Really Long Keyword
#!  ^^^^^^^^^^^^^^^^^^^ Undefined keyword: Really Long Keyword.

Similar To Really Long Keyword
    [Documentation]    FAIL
    ...    No keyword with name 'Reallly Long Keyword that doesn't end for a while' found. Did you mean:
    ...    ${INDENT}Really Long Keyword That Does Not End For Quite A While
    Reallly Long Keyword that doesn't end for a while
#!  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ Undefined keyword: Reallly Long Keyword that doesn't end for a while.

Misspelled Keyword With Arguments
    [Documentation]    FAIL
    ...    No keyword with name 'recoord' found. Did you mean:
    ...    ${INDENT}RecLibrary1.Record
    recoord    message=hello world    level=WARN
#!  ^^^^^^^ Undefined keyword: recoord.

Just Library Name
    [Documentation]    FAIL    No keyword with name 'RecLibrary1' found.
    RecLibrary1
#!  ^^^^^^^^^^^ Undefined keyword: RecLibrary1.

Leading Period Keyword
    [Documentation]    FAIL    No keyword with name '.Nothing' found.
    .Nothing
#!  ^^^^^^^^ Undefined keyword: .Nothing.

Leading Period Library Name
    [Documentation]    FAIL    No keyword with name '.RecLibrary1' found.
    .RecLibrary1
#!  ^^^^^^^^^^^^ Undefined keyword: .RecLibrary1.

Ending In Period Keyword
    [Documentation]    FAIL    No keyword with name 'Nothing.' found.
    Nothing.
#!  ^^^^^^^^ Undefined keyword: Nothing..

Ending In Period Library Name
    [Documentation]    FAIL    No keyword with name 'RecLibrary1.' found.
    RecLibrary1.
#!  ^^^^^^^^^^^^ Undefined keyword: RecLibrary1..

Period
    [Documentation]    FAIL    No keyword with name '.' found.
    .
#!  ^ Undefined keyword: ..

Underscore
    [Documentation]    FAIL    No keyword with name '_' found.
    _
#!  ^ Undefined keyword: _.

Dollar
    [Documentation]    FAIL    No keyword with name '$' found.
    $
#!  ^ Undefined keyword: $.

Curly Brace
    [Documentation]    FAIL    No keyword with name '{}' found.
    {}
#!  ^^ Undefined keyword: {}.

More Non-ASCII
    [Documentation]    FAIL    No keyword with name 'ლ(ಠ益ಠლ)' found.
    ლ(ಠ益ಠლ)
#!  ^^^^^^^ Undefined keyword: ლ(ಠ益ಠლ).

Non-ASCII But Similar
    [Documentation]    FAIL
    ...    No keyword with name 'Similär Kw' found. Did you mean:
    ...    ${INDENT}Similar Kw 5
    ...    ${INDENT}Rec Library 2 With Custom Name.Similar Kw 4
    ...    ${INDENT}RecLibrary1.Similar Kw 3
    ...    ${INDENT}recommendation_resource_2.Similar Kw 2
    ...    ${INDENT}recommendation_resource_1.Similar Kw 1
    Similär Kw
#!  ^^^^^^^^^^ Undefined keyword: Similär Kw.

Explicit Many Similar Keywords
    [Documentation]    FAIL
    ...    No keyword with name 'RecLibrary1.Edit Data' found. Did you mean:
    ...    ${INDENT}RecLibrary1.Get Data
    ...    ${INDENT}RecLibrary1.Read Data
    ...    ${INDENT}RecLibrary1.Update Data
    ...    ${INDENT}RecLibrary1.Modify Data
    ...    ${INDENT}RecLibrary1.Delete Data
    ...    ${INDENT}RecLibrary1.Create Data
    RecLibrary1.Edit Data
#!  ^^^^^^^^^^^^^^^^^^^^^ Undefined keyword: RecLibrary1.Edit Data.

Implicit Many Similar Keywords
    [Documentation]    FAIL
    ...    No keyword with name 'Edit Data' found. Did you mean:
    ...    ${INDENT}RecLibrary1.Get Data
    ...    ${INDENT}RecLibrary1.Read Data
    Edit Data
#!  ^^^^^^^^^ Undefined keyword: Edit Data.

Explicit Substring Of Many Keywords
    [Documentation]    FAIL
    ...    No keyword with name 'RecLibrary1.Data' found. Did you mean:
    ...    ${INDENT}RecLibrary1.Get Data
    ...    ${INDENT}RecLibrary1.Read Data
    RecLibrary1.Data
#!  ^^^^^^^^^^^^^^^^ Undefined keyword: RecLibrary1.Data.

Implicit Substring Of Many Keywords
    [Documentation]    FAIL
    ...    No keyword with name 'Data' found. Did you mean:
    ...    ${INDENT}RecLibrary1.Get Data
    ...    ${INDENT}RecLibrary1.Read Data
    Data
#!  ^^^^ Undefined keyword: Data.

Missing separator between keyword and arguments
    [Documentation]    FAIL
    ...    No keyword with name 'Should Be Equal ${variable} 42' found. \
    ...    Did you try using keyword 'BuiltIn.Should Be Equal' and \
    ...    forgot to use enough whitespace between keyword and arguments?
    Should Be Equal ${variable} 42
#!                    ^^^^^^^^ Undefined variable: variable

Missing separator between keyword and arguments with multiple matches
    [Documentation]    FAIL
    ...    No keyword with name 'Should Be Equal As Integers ${variable} 42' found. \
    ...    Did you try using keyword 'BuiltIn.Should Be Equal' or \
    ...    'BuiltIn.Should Be Equal As Integers' and \
    ...    forgot to use enough whitespace between keyword and arguments?
    Should Be Equal As Integers ${variable} 42
#!                                ^^^^^^^^ Undefined variable: variable

*** Keywords ***
A User Keyword
    No Operation
#!  ^^^^^^^^^^^^ Multiple keywords matching: 'No Operation' in 'BuiltIn', 'Rec Library 2 With Custom Name', 'RecLibrary1'.
#!  ^^^^^^^^^^^^ Please provide the name with the full qualifier (i.e.: 'BuiltIn.No Operation').

Similar User Keyword 1
    No Operation
#!  ^^^^^^^^^^^^ Multiple keywords matching: 'No Operation' in 'BuiltIn', 'Rec Library 2 With Custom Name', 'RecLibrary1'.
#!  ^^^^^^^^^^^^ Please provide the name with the full qualifier (i.e.: 'BuiltIn.No Operation').

Similar User Keyword 2
    No Operation
#!  ^^^^^^^^^^^^ Multiple keywords matching: 'No Operation' in 'BuiltIn', 'Rec Library 2 With Custom Name', 'RecLibrary1'.
#!  ^^^^^^^^^^^^ Please provide the name with the full qualifier (i.e.: 'BuiltIn.No Operation').

Similar User Keyword 3
    No Operation
#!  ^^^^^^^^^^^^ Multiple keywords matching: 'No Operation' in 'BuiltIn', 'Rec Library 2 With Custom Name', 'RecLibrary1'.
#!  ^^^^^^^^^^^^ Please provide the name with the full qualifier (i.e.: 'BuiltIn.No Operation').

Embedded User ${hello} Argument ${world} Keyword 1
    No Operation
#!  ^^^^^^^^^^^^ Multiple keywords matching: 'No Operation' in 'BuiltIn', 'Rec Library 2 With Custom Name', 'RecLibrary1'.
#!  ^^^^^^^^^^^^ Please provide the name with the full qualifier (i.e.: 'BuiltIn.No Operation').

Embedded User ${foo} Argument ${bar} Keyword 2
    No Operation
#!  ^^^^^^^^^^^^ Multiple keywords matching: 'No Operation' in 'BuiltIn', 'Rec Library 2 With Custom Name', 'RecLibrary1'.
#!  ^^^^^^^^^^^^ Please provide the name with the full qualifier (i.e.: 'BuiltIn.No Operation').

Unique ${i} Kw ${j}
    No Operation
#!  ^^^^^^^^^^^^ Multiple keywords matching: 'No Operation' in 'BuiltIn', 'Rec Library 2 With Custom Name', 'RecLibrary1'.
#!  ^^^^^^^^^^^^ Please provide the name with the full qualifier (i.e.: 'BuiltIn.No Operation').

Key.word.with periods.
    No Operation
#!  ^^^^^^^^^^^^ Multiple keywords matching: 'No Operation' in 'BuiltIn', 'Rec Library 2 With Custom Name', 'RecLibrary1'.
#!  ^^^^^^^^^^^^ Please provide the name with the full qualifier (i.e.: 'BuiltIn.No Operation').

hyvää yötä
    No Operation
#!  ^^^^^^^^^^^^ Multiple keywords matching: 'No Operation' in 'BuiltIn', 'Rec Library 2 With Custom Name', 'RecLibrary1'.
#!  ^^^^^^^^^^^^ Please provide the name with the full qualifier (i.e.: 'BuiltIn.No Operation').

Really long keyword that does not end for quite a while
    No Operation
#!  ^^^^^^^^^^^^ Multiple keywords matching: 'No Operation' in 'BuiltIn', 'Rec Library 2 With Custom Name', 'RecLibrary1'.
#!  ^^^^^^^^^^^^ Please provide the name with the full qualifier (i.e.: 'BuiltIn.No Operation').

Similar Kw 5
    No Operation
#!  ^^^^^^^^^^^^ Multiple keywords matching: 'No Operation' in 'BuiltIn', 'Rec Library 2 With Custom Name', 'RecLibrary1'.
#!  ^^^^^^^^^^^^ Please provide the name with the full qualifier (i.e.: 'BuiltIn.No Operation').
