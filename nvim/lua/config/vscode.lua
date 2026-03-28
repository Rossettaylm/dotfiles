-- VSCode-specific keymaps via vscode-neovim
-- 仅在 vim.g.vscode == true 时由 init.lua 加载

local vscode = require("vscode")
local keymap = vim.keymap.set

local n = "n"
local v = "x"
local nv = { "n", "x" }

-- ============================================
-- 基础编辑
-- ============================================

keymap(n, "q", function() vscode.action("workbench.action.closeActiveEditor") end, { desc = "Close editor" })
keymap(n, "S", function() vscode.action("workbench.action.files.save") end, { desc = "Save file" })

-- change 不进入剪贴板
keymap(nv, "c", '"_c', { desc = "Change without yank" })
keymap(nv, "C", '"_C', { desc = "Change line without yank" })

-- visual 模式粘贴不污染剪贴板
keymap(v, "p", '"_dP', { desc = "Paste without yank" })

-- switch case
keymap(nv, "`", "~", { desc = "Switch case" })

-- redo
keymap(n, "U", "<C-r>", { desc = "Redo" })

-- yank/paste word shortcuts
keymap(n, "Y", "yiw", { desc = "Yank inner word" })
keymap(n, "P", "viwp", { desc = "Paste over inner word" })

-- search navigation (centered)
keymap(nv, "=", "nzz", { desc = "Next search result (centered)" })
keymap(nv, "-", "Nzz", { desc = "Prev search result (centered)" })

-- 复制上一条记录
keymap(n, "<leader>p", '"0p', { desc = "Paste from yank register" })

-- ============================================
-- 导航
-- ============================================

keymap(n, "[[", function() vscode.action("workbench.action.navigateBack") end, { desc = "Navigate back" })
keymap(n, "]]", function() vscode.action("workbench.action.navigateForward") end, { desc = "Navigate forward" })

-- Tab 切换
keymap(n, "[b", function() vscode.action("workbench.action.previousEditor") end, { desc = "Previous tab" })
keymap(n, "]b", function() vscode.action("workbench.action.nextEditor") end, { desc = "Next tab" })

-- ============================================
-- 搜索与跳转
-- ============================================

keymap(n, "<leader><leader>", function() vscode.action("workbench.action.openRecent") end, { desc = "Recent files" })
keymap(n, "<leader>,", function() vscode.action("workbench.action.quickOpen") end, { desc = "Go to file" })
keymap(n, "<leader><cr>", function() vscode.action("workbench.action.showCommands") end, { desc = "Command palette" })
keymap(n, "<leader>ps", function() vscode.action("workbench.action.showAllSymbols") end, { desc = "Go to symbol in workspace" })
keymap(n, "<leader>pt", function() vscode.action("workbench.action.findInFiles") end, { desc = "Search in files" })
keymap(n, "<leader>pa", function() vscode.action("workbench.action.showCommands") end, { desc = "Command palette" })
keymap(n, "<leader>o", function() vscode.action("workbench.action.gotoSymbol") end, { desc = "Go to symbol in editor" })
keymap(n, "?", function() vscode.action("actions.find") end, { desc = "Find in file" })

-- ============================================
-- 代码操作
-- ============================================

keymap(n, "gd", function() vscode.action("editor.action.revealDefinition") end, { desc = "Go to definition" })
keymap(n, "gi", function() vscode.action("editor.action.goToImplementation") end, { desc = "Go to implementation" })
keymap(n, "ga", function() vscode.action("editor.action.goToReferences") end, { desc = "Find all references" })
keymap(n, "gh", function() vscode.action("editor.action.showHover") end, { desc = "Show hover" })
keymap(n, "ge", function() vscode.action("editor.action.marker.next") end, { desc = "Next problem/error" })
keymap(n, "<leader>rn", function() vscode.action("editor.action.rename") end, { desc = "Rename symbol" })
keymap(n, "<leader>.", function() vscode.action("editor.action.quickFix") end, { desc = "Quick fix / code actions" })
keymap(nv, "<leader>cf", function() vscode.action("editor.action.formatDocument") end, { desc = "Format document" })
keymap(n, "go", function() vscode.action("editor.action.organizeImports") end, { desc = "Organize imports" })

-- ============================================
-- 折叠
-- ============================================

keymap(n, "co", function() vscode.action("editor.fold") end, { desc = "Fold region" })
keymap(n, "ep", function() vscode.action("editor.unfold") end, { desc = "Unfold region" })
keymap(n, "<leader>co", function() vscode.action("editor.foldAll") end, { desc = "Fold all" })
keymap(n, "<leader>ep", function() vscode.action("editor.unfoldAll") end, { desc = "Unfold all" })

-- ============================================
-- 窗口导航
-- ============================================

keymap(n, "<C-h>", function() vscode.action("workbench.action.focusLeftGroup") end, { desc = "Focus left group" })
keymap(n, "<C-j>", function() vscode.action("workbench.action.focusBelowGroup") end, { desc = "Focus below group" })
keymap(n, "<C-k>", function() vscode.action("workbench.action.focusAboveGroup") end, { desc = "Focus above group" })
keymap(n, "<C-l>", function() vscode.action("workbench.action.focusRightGroup") end, { desc = "Focus right group" })

keymap(n, "<leader>sl", function() vscode.action("workbench.action.splitEditorRight") end, { desc = "Split editor right" })
keymap(n, "<leader>sj", function() vscode.action("workbench.action.splitEditorDown") end, { desc = "Split editor down" })

-- ============================================
-- 调试
-- ============================================

keymap(n, "\\d,", function() vscode.action("workbench.action.debug.continue") end, { desc = "Debug continue" })
keymap(n, "\\d.", function() vscode.action("workbench.action.debug.stop") end, { desc = "Debug stop" })
keymap(n, "\\dn", function() vscode.action("workbench.action.debug.stepOver") end, { desc = "Debug step over" })
keymap(n, "\\di", function() vscode.action("workbench.action.debug.stepInto") end, { desc = "Debug step into" })
keymap(n, "\\do", function() vscode.action("workbench.action.debug.stepOut") end, { desc = "Debug step out" })

keymap(n, "\\ba", function() vscode.action("editor.debug.action.toggleBreakpoint") end, { desc = "Toggle breakpoint" })
keymap(n, "\\bb", function() vscode.action("workbench.debug.action.toggleRepl") end, { desc = "Toggle debug console" })

-- ============================================
-- 杂项
-- ============================================

keymap(n, "<leader>y", function() vscode.action("copyRelativeFilePath") end, { desc = "Copy relative file path" })
keymap(n, "gl", function() vscode.action("gitlens.toggleFileBlame") end, { desc = "Toggle line blame" })
keymap(n, "<c-/>", function() vscode.action("workbench.action.terminal.toggleTerminal") end, { desc = "Toggle terminal" })

-- select word (对应 .ideavimrc 的 <cr> -> EditorSelectWord)
keymap(n, "<cr>", function() vscode.action("editor.action.smartSelect.expand") end, { desc = "Expand selection" })
keymap(v, "<cr>", function() vscode.action("actions.find") end, { desc = "Find selected text" })

-- zen mode
keymap(n, "zm", function() vscode.action("workbench.action.toggleZenMode") end, { desc = "Toggle zen mode" })

-- bookmark (需要 Bookmarks 扩展)
keymap(n, "ma", function() vscode.action("bookmarks.toggle") end, { desc = "Toggle bookmark" })
keymap(n, "mm", function() vscode.action("bookmarks.listFromAllFiles") end, { desc = "List all bookmarks" })
