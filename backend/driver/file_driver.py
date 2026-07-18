import os
import re
import mimetypes
import logging
from typing import Dict, Any, List, Tuple
import json
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("FileDriver")

class FileDriver:
    """
    Driver specialized in managing, writing, reading and mapping
    the file system (Workspace) for an AI Agent. Operates in an OS-agnostic manner.
    """

    def __init__(self, workspace_root: str = None):
        # Initializes the agent's project root directory
        self.workspace_root = os.path.abspath(workspace_root) if workspace_root else os.getcwd()
        logger.info(f"[FileDriver] Workspace root set to: {self.workspace_root}")

    def _get_relative_path(self, path: str) -> str:
        """Internal helper to secure and return a relative path from the workspace."""
        abs_path = os.path.abspath(os.path.join(self.workspace_root, path))
        # Basic protection against directory traversal attacks (../)
        if not abs_path.startswith(self.workspace_root):
            raise PermissionError(f"Access denied outside the Workspace: {path}")
        return abs_path

    def write_file(self, file_path: str, content: str) -> Tuple[str, int]:
        """
        [FUNCTION 1] Writes or overwrites a file (code, md, txt, docs, json, etc.).
        Automatically creates parent subdirectories if necessary.
        """
        try:
            target_path = self._get_relative_path(file_path)
            # Automatic creation of missing intermediate directories
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(content)
                
            logger.info(f"File saved: {file_path}")
            return f"File successfully created/updated: {file_path}", 0
        except Exception as e:
            return f"Error writing file: {str(e)}", -1

    def read_file(self, file_path: str, max_chars: int = 8000) -> Tuple[str, int]:
        """
        [FUNCTION 2] Reads the textual content of a file.
        Includes anti-saturation protection if the code file is huge.
        """
        try:
            target_path = self._get_relative_path(file_path)
            if not os.path.exists(target_path):
                return f"Error: The file '{file_path}' does not exist.", 1
            if not os.path.isfile(target_path):
                return f"Error: '{file_path}' is a directory, not a file.", 1

            # Quick detection of binary files to avoid injecting unreadable noise into the LLM
            mime_type, _ = mimetypes.guess_type(target_path)
            if mime_type and not mime_type.startswith("text/") and "json" not in mime_type and "javascript" not in mime_type:
                return f"Read refused: The file '{file_path}' appears to be a binary ({mime_type}).", 1

            with open(target_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            # Context anti-saturation
            if len(content) > max_chars:
                truncated_count = len(content) - max_chars
                return f"{content[:max_chars]}\n\n[... SEMANTIC OMISSION: {truncated_count} characters truncated by FileDriver to preserve context ...]", 0
            
            return content, 0
        except Exception as e:
            return f"Error reading file: {str(e)}", -1

    def search_in_files(self, pattern: str, extension_filter: str = None) -> Tuple[str, int]:
        """
        [FUNCTION 3] Native Grep engine. Searches for a text pattern or Regex
        in all text files of the project.
        """
        try:
            regex = re.compile(pattern, re.IGNORECASE)
            matches = []
            
            # Recursive traversal of the workspace
            for root, _, files in os.walk(self.workspace_root):
                # Ignore heavy or hidden directories (.git, __pycache__, venv)
                if any(ignored in root for ignored in [".git", "__pycache__", "node_modules", "venv", ".pytest_cache"]):
                    continue
                    
                for file in files:
                    if extension_filter and not file.endswith(extension_filter):
                        continue
                        
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, self.workspace_root)
                    
                    try:
                        with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                            for line_num, line in enumerate(f, 1):
                                if regex.search(line):
                                    matches.append(f"  - {rel_path} [Line {line_num}] : {line.strip()}")
                    except Exception:
                        pass # Ignore files that are not readable as text during traversal
                        
            if not matches:
                return f"No results found for pattern: '{pattern}'", 0
                
            result_str = f"SEARCH RESULTS FOR '{pattern}':\n" + "\n".join(matches)
            return result_str, 0
        except Exception as e:
            return f"Error during semantic search: {str(e)}", -1

    def get_folder_cartography(self) -> Dict[str, Any]:
        """
        [FUNCTION 4] Workspace tree Mapping.
        Generates a pure, compact hierarchical dictionary structure
        perfectly readable by an LLM.
        """
        def _build_tree(dir_path: str) -> Dict[str, Any]:
            tree = {"name": os.path.basename(dir_path), "type": "directory", "children": []}
            try:
                for entry in os.scandir(dir_path):
                    # Exclusion filters for technical directories to lighten the AI's view
                    if entry.name in [".git", "__pycache__", "node_modules", "venv", ".pytest_cache", ".DS_Store"]:
                        continue
                        
                    if entry.is_dir(follow_symlinks=False):
                        tree["children"].append(_build_tree(entry.path))
                    else:
                        tree["children"].append({
                            "name": entry.name,
                            "type": "file",
                            "size_bytes": entry.stat().st_size
                        })
            except Exception as e:
                tree["error"] = str(e)
            return tree

        # Starts recursive mapping from the workspace root
        return _build_tree(self.workspace_root)


# =====================================================================
# FILE TOOLKIT VALIDATION SCRIPT
# =====================================================================
if __name__ == "__main__":
    # Instantiate the driver in the current test directory
    file_manager = FileDriver()
    
    print("\n--- TEST 1: WRITING DIFFERENT FILES (CODE & MD) ---")
    file_manager.write_file("src/math_module.py", "def add(a, b):\n    return a + b\n")
    file_manager.write_file("docs/README.md", "# Agent Documentation\nThis project uses a dedicated FileDriver.")
    
    print("\n--- TEST 2: SEMANTIC WORKSPACE MAPPING FOR THE LLM ---")
    carto = file_manager.get_folder_cartography()
    print(json.dumps(carto, indent=2, ensure_ascii=False))

    print("\n--- TEST 3: TEXT SEARCH (NATIVE GREP) ---")
    search_log, _ = file_manager.search_in_files("def add")
    print(search_log)

    print("\n--- TEST 4: SECURE FILE READING ---")
    content, _ = file_manager.read_file("src/math_module.py")
    print(f"Content read:\n{content}")