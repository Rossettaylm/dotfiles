-- =============================================
-- Navigation mode: auto / full / lite
-- =============================================

local M = {}

local VALID_MODE = {
  auto = true,
  full = true,
  lite = true,
}

local DEFAULTS = {
  mode = "auto",
  large_file_bytes = 512 * 1024,
  large_file_lines = 12000,
}

local function normalize_buf(buf)
  if not buf or buf == 0 then
    return vim.api.nvim_get_current_buf()
  end
  return buf
end

local function to_number(value, fallback)
  local num = tonumber(value)
  if num and num > 0 then
    return math.floor(num)
  end
  return fallback
end

local function selected_mode()
  local raw = (vim.g.nav_mode or os.getenv("NVIM_NAV_MODE") or DEFAULTS.mode)
  local mode = tostring(raw):lower()
  if VALID_MODE[mode] then
    return mode
  end
  return DEFAULTS.mode
end

local function large_file_limits()
  local bytes = to_number(vim.g.nav_large_file_bytes or os.getenv("NVIM_NAV_LARGE_FILE_BYTES"), DEFAULTS.large_file_bytes)
  local lines = to_number(vim.g.nav_large_file_lines or os.getenv("NVIM_NAV_LARGE_FILE_LINES"), DEFAULTS.large_file_lines)
  return bytes, lines
end

local function root_mode_hint(buf)
  local name = vim.api.nvim_buf_get_name(buf)
  if name == "" then
    return nil
  end

  local root = vim.fs.root(name, { ".nvim-lite", ".nvim-full", ".git" })
  if not root then
    return nil
  end

  if vim.uv.fs_stat(root .. "/.nvim-lite") then
    return "lite"
  end

  if vim.uv.fs_stat(root .. "/.nvim-full") then
    return "full"
  end

  return nil
end

local function supports_treesitter(buf)
  if not vim.api.nvim_buf_is_valid(buf) or vim.bo[buf].buftype ~= "" then
    return false
  end

  local ok_lang, language = pcall(vim.treesitter.language.get_lang, vim.bo[buf].filetype)
  if not ok_lang or not language then
    return false
  end

  local ok_inspect = pcall(vim.treesitter.language.inspect, language)
  return ok_inspect
end

local function is_large_buffer(buf)
  if not vim.api.nvim_buf_is_valid(buf) or vim.bo[buf].buftype ~= "" then
    return false
  end

  local max_bytes, max_lines = large_file_limits()
  local name = vim.api.nvim_buf_get_name(buf)

  if name ~= "" then
    local stat = vim.uv.fs_stat(name)
    if stat and stat.size and stat.size > max_bytes then
      return true
    end
  end

  local ok, line_count = pcall(vim.api.nvim_buf_line_count, buf)
  return ok and line_count > max_lines
end

local function retrigger_filetype(buf)
  local filetype = vim.bo[buf].filetype
  if filetype == "" then
    return
  end

  vim.schedule(function()
    if vim.api.nvim_buf_is_valid(buf) then
      vim.api.nvim_exec_autocmds("FileType", { buffer = buf, modeline = false })
    end
  end)
end

function M.selected_mode()
  return selected_mode()
end

function M.mode_for(buf)
  buf = normalize_buf(buf)

  local mode = selected_mode()
  if mode ~= "auto" then
    return mode
  end

  local hint = root_mode_hint(buf)
  if hint then
    return hint
  end

  if not supports_treesitter(buf) then
    return "lite"
  end

  if is_large_buffer(buf) then
    return "lite"
  end

  return "full"
end

function M.is_full(buf)
  return M.mode_for(buf) == "full"
end

function M.is_lite(buf)
  return M.mode_for(buf) == "lite"
end

function M.should_use_treesitter(buf)
  return M.is_full(buf)
end

function M.disable_treesitter(buf)
  buf = normalize_buf(buf)

  pcall(vim.treesitter.stop, buf)

  local indentexpr = vim.bo[buf].indentexpr or ""
  if string.find(indentexpr, "nvim-treesitter", 1, true) then
    vim.bo[buf].indentexpr = ""
  end

  for _, win in ipairs(vim.fn.win_findbuf(buf)) do
    local foldexpr = vim.wo[win].foldexpr or ""
    if string.find(foldexpr, "vim.treesitter.foldexpr", 1, true) then
      vim.wo[win].foldmethod = "manual"
      vim.wo[win].foldexpr = "0"
      vim.wo[win].foldlevel = 99
    end
  end
end

function M.apply(buf, opts)
  opts = opts or {}
  buf = normalize_buf(buf)
  if not vim.api.nvim_buf_is_valid(buf) then
    return
  end

  if M.is_lite(buf) then
    M.disable_treesitter(buf)
    return
  end

  if opts.force_attach then
    retrigger_filetype(buf)
  end
end

function M.describe(buf)
  buf = normalize_buf(buf)

  local selected = M.selected_mode()
  local effective = M.mode_for(buf)
  local max_bytes, max_lines = large_file_limits()

  return string.format(
    "selected=%s effective=%s thresholds=%dB/%dL",
    selected,
    effective,
    max_bytes,
    max_lines
  )
end

function M.set_mode(mode)
  local next_mode = tostring(mode or ""):lower()
  if not VALID_MODE[next_mode] then
    vim.notify("Invalid nav mode: " .. next_mode .. " (auto/full/lite)", vim.log.levels.ERROR, { title = "Nav Mode" })
    return
  end

  vim.g.nav_mode = next_mode

  local should_force_attach = next_mode ~= "lite"
  for _, buf in ipairs(vim.api.nvim_list_bufs()) do
    if vim.api.nvim_buf_is_loaded(buf) then
      M.apply(buf, { force_attach = should_force_attach })
    end
  end

  vim.notify("Navigation mode => " .. M.describe(0), vim.log.levels.INFO, { title = "Nav Mode" })
end

function M.open_symbols()
  local ok_fzf, fzf = pcall(require, "fzf-lua")
  if not ok_fzf then
    vim.notify("fzf-lua is unavailable", vim.log.levels.WARN, { title = "Nav Mode" })
    return
  end

  local has_lsp = #vim.lsp.get_clients({ bufnr = 0 }) > 0
  if has_lsp then
    fzf.lsp_document_symbols()
    return
  end

  if M.is_full(0) and type(fzf.treesitter) == "function" then
    local actions = require("fzf-lua.actions")
    local ok_ts = pcall(fzf.treesitter, {
      actions = {
        ["default"] = actions.file_edit,
        ["ctrl-s"] = actions.file_split,
        ["ctrl-v"] = actions.file_vsplit,
        ["ctrl-t"] = actions.file_tabedit,
      },
    })
    if ok_ts then
      return
    end
  end

  if M.is_full(0) then
    local ok_lazy, lazy = pcall(require, "lazy")
    if ok_lazy then
      lazy.load({ plugins = { "aerial.nvim" } })
    end

    local ok_aerial, aerial = pcall(require, "aerial")
    if ok_aerial then
      aerial.toggle({ focus = true })
      return
    end
  end

  fzf.lgrep_curbuf()
end

function M.flash_treesitter_or_jump()
  local ok_flash, flash = pcall(require, "flash")
  if not ok_flash then
    return
  end

  if M.is_full(0) then
    local ok_ts = pcall(flash.treesitter)
    if ok_ts then
      return
    end
  end

  flash.jump()
end

function M.setup()
  vim.g.nav_mode = selected_mode()

  if vim.g.vscode then
    return
  end

  vim.api.nvim_create_user_command("NavMode", function(opts)
    if opts.args == "" then
      vim.notify(M.describe(0), vim.log.levels.INFO, { title = "Nav Mode" })
      return
    end
    M.set_mode(opts.args)
  end, {
    nargs = "?",
    desc = "Navigation mode: auto/full/lite",
    complete = function()
      return { "auto", "full", "lite" }
    end,
  })

  vim.api.nvim_create_user_command("NavModeInfo", function()
    vim.notify(M.describe(0), vim.log.levels.INFO, { title = "Nav Mode" })
  end, { desc = "Show effective navigation mode" })

  vim.keymap.set("n", "<leader>ta", function()
    M.set_mode("auto")
  end, { desc = "Navigation mode: auto" })

  vim.keymap.set("n", "<leader>tf", function()
    M.set_mode("full")
  end, { desc = "Navigation mode: full" })

  vim.keymap.set("n", "<leader>tl", function()
    M.set_mode("lite")
  end, { desc = "Navigation mode: lite" })

  vim.keymap.set("n", "<leader>tm", function()
    vim.notify(M.describe(0), vim.log.levels.INFO, { title = "Nav Mode" })
  end, { desc = "Navigation mode info" })

  vim.api.nvim_create_autocmd({ "BufReadPost", "BufWinEnter" }, {
    group = vim.api.nvim_create_augroup("nav-mode-sync", { clear = true }),
    callback = function(args)
      M.apply(args.buf)
    end,
  })
end

return M
