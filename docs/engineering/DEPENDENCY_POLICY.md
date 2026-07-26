# Dependency policy

Direct dependencies MUST have a reason and an owner within the package that
uses them. Commit lockfiles, separate runtime/test/dev groups, audit direct and
transitive vulnerabilities and licenses, remove unused packages, and disable
unneeded default features. Avoid duplicate libraries without a documented
boundary benefit. Review dependency size, build time, cold start, browser
transfer, and supply-chain exposure before adding convenience dependencies.

Anti-patterns include unpinned resolution, copied transitive APIs, unused
framework bundles, blanket feature activation, and a dependency added only to
avoid a small standard-library function. Evidence is manifest, lockfile, audit
output, and measured impact; no universal benchmark claim is inferred.

## Primary sources

[Cargo dependencies](https://doc.rust-lang.org/cargo/reference/specifying-dependencies.html),
[Go modules](https://go.dev/ref/mod), and
[Python packaging](https://packaging.python.org/en/latest/).

<a id="dep-001"></a>
