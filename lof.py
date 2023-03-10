from argparse import ArgumentParser
from clang.cindex import CompilationDatabase, Config, Cursor, CursorKind, Index, SourceRange, TranslationUnitLoadError
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import logging
import os


@dataclass
class FunctionEntry:
    name: str
    node: Cursor

    @property
    def extent(self) -> SourceRange:
        assert self.node
        return self.node.extent

    @property
    def lines(self) -> int:
        if not self.extent:
            return 0

        start_line = self.extent.start.line
        end_line = self.extent.end.line
        return end_line - start_line


def tu_from_source(source: Path, compilation_args):
    index = Index.create()
    logging.info(f"parsing: {source}")
    translation_unit = index.parse(str(source), compilation_args)
    return translation_unit


def fully_qualified(c):
    try:
        if c is None:
            return ''
        elif c.kind == CursorKind.TRANSLATION_UNIT:
            return ''
        else:
            par = c.semantic_parent
            res = fully_qualified(c.semantic_parent)
            if res != '':
                return res + '::' + c.spelling
        return c.spelling
    except ValueError:
        return ''


def list_of_functions(root, indent=0) -> List[str]:
    function_names = []
    all_fn_types = [
        CursorKind.FUNCTION_DECL,
        CursorKind.CONSTRUCTOR,
        CursorKind.CXX_METHOD,
        CursorKind.FUNCTION_TEMPLATE
    ]

    all_qual_kinds = [
        CursorKind.CLASS_DECL,
        CursorKind.NAMESPACE,
    ]

    for node in root.get_children():
        logging.debug(f'{"  "*indent} {node.kind} - {node.displayname}')
        if node.kind in all_fn_types:
            function_names.append(FunctionEntry(f"{fully_qualified(node.semantic_parent)}::{node.displayname}", node))
        elif node.kind in all_qual_kinds:
            function_names.extend(list_of_functions(node, indent+2))
    return function_names


def compile_commands_from_db(db: Optional[Path], source: Path):
    if not db:
        return []

    cc_db = CompilationDatabase.fromDirectory(db)
    source_file = source.absolute()
    compile_commands = [c for c in cc_db.getCompileCommands(source_file)]
    compilation_args = [arg for arg in compile_commands[0].arguments]
    return compilation_args


def compilation_args_from_db(db: Optional[Path], source: Path) -> List[str]:
    full_command = compile_commands_from_db(db, source)

    filtered_args = []
    for idx in range(len(full_command)):
        arg = full_command[idx]
        if arg.startswith("-I") or arg.startswith("-D"):
            filtered_args.append(arg)

        if arg == "-isystem":
            assert idx < len(full_command), "-isystem requires a second argument"
            filtered_args.append(arg)
            filtered_args.append(full_command[idx + 1])

    return filtered_args


def filter_empty_functions(functions: List[FunctionEntry]) -> List[FunctionEntry]:
    return [
        fn for fn in functions
        if fn.lines > 0
    ]


def order_by_lines(functions: List[FunctionEntry]) -> List[FunctionEntry]:
    return sorted(
        functions,
        key = lambda fn: fn.lines
    )


def functions_from_file(db: Path, source: Path) -> List[FunctionEntry]:
    compilation_args = compilation_args_from_db(db, source)

    try:
        translation_unit = tu_from_source(source, compilation_args)
    except TranslationUnitLoadError:
        logging.warning(f"warning: Couldn't parse file {source}!")
        return []

    functions = list_of_functions(translation_unit.cursor)
    return filter_empty_functions(functions)


def source_files_from_db(db: Path) -> List[Path]:
    cc_db = CompilationDatabase.fromDirectory(db)
    return [Path(command.filename) for command in cc_db.getAllCompileCommands()]


def main():
    parser = ArgumentParser()
    parser.add_argument('source', nargs='?', type=Path, help="C/C++ source file to list the functions and the number of lines")
    parser.add_argument('-p', '--compilation-database', type=Path, help="Path to the compilation database, if there is one")
    parser.add_argument('-l', '--library-path', type=Path, default=os.environ.get('CLANG_LIBRARY_PATH', ''), help="Path to the clang libraries. Default is from the env variable CLANG_LIBRARY_PATH")
    parser.add_argument('-m', '--max-sources', type=int, help='For debugging, limits the number of files processed')
    parser.add_argument('-ll', '--log', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help='Log verbosity')
    args = parser.parse_args()

    if args.library_path == '':
        logging.error('Must specify library-path or CLANG_LIBRARY_PATH env variable!')
        exit(1)

    if args.log:
        logging.basicConfig(level=getattr(logging, args.log))

    Config.set_library_path(args.library_path)

    if args.source:
        functions = functions_from_file(args.compilation_database, args.source)
    else:
        if not args.compilation_database:
            raise RuntimeError("compilation database not specified")
        source_files = source_files_from_db(args.compilation_database)
        if args.max_sources:
            source_files = source_files[:args.max_sources]
        functions = sum([
            functions_from_file(args.compilation_database, source_file)
            for source_file in source_files
        ], [])

    functions = order_by_lines(functions)
    for fn in functions:
        print(f"{fn.name}: {fn.lines} lines")

if __name__ == '__main__':
    main()