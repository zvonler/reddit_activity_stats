
PYTHON=/opt/homebrew/bin/python3.11

venv: venv_reqs.txt
	$(PYTHON) -m venv venv
	venv/bin/pip install -r venv_reqs.txt
	$(eval PWD=$(shell pwd -P))
	echo "$(PWD)/src/main/python" > venv/lib/python3.11/site-packages/zxv.pth
