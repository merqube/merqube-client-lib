VERSION = $(shell poetry version | cut -d' ' -f2)

tag:
	git tag -a $(VERSION) -m "version $(VERSION)"
	git push -u origin main
	git push -u origin $(VERSION)
