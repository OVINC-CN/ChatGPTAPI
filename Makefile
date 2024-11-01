pylint:
	scripts/pylint.sh

pre-commit:
	scripts/pre-commit.sh

lint: pre-commit pylint
