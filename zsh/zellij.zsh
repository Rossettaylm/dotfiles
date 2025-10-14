# auto enter zellij
if [[ $(which zellij) ]]; then
  if [[ ! -v ZELLIJ ]]; then 
    zellij
  fi
fi
