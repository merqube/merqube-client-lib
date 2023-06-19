VERSION = $(shell poetry version | cut -d' ' -f2)

# in cicd (circle) this uses the merqube-pub machine user via UserKeys in circle ci
tag:
	git config --global user.email "tommy-gh@merqube"
	git config --global user.name "merqube-pub"
	git tag -a $(VERSION) -m "version $(VERSION)"
	git push -u origin main
	git push -u origin $(VERSION)
