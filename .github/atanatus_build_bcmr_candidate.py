from pathlib import Path

path = Path("workers/src/bcmr_onchain.rs")
s = path.read_text(encoding="utf-8")


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 anchor, found {count}")
    return source.replace(old, new, 1)


old = 'const BCMR_MAGIC: [u8; 4] = *b"BCMR";'
new = old + '\nconst BCMR_WELL_KNOWN_PATH: &str = "/.well-known/bitcoin-cash-metadata-registry.json";'
s = replace_once(s, old, new, "constant")

fetch_doc = '/// Fetch the BCMR JSON pointed at by `uri` and verify its sha256 matches'
resolver = '''/// Resolve a BCMR publication URI using BCMR-specific HTTPS semantics.
///
/// Publication URIs without a protocol are HTTPS. For HTTPS publications,
/// a hostname without an explicit file path resolves to the registry's
/// Well-Known URI. A trailing slash is significant: it explicitly selects
/// the domain root and must not be rewritten.
fn resolve_bcmr_uri(uri: &str) -> Option<String> {
    let trimmed = uri.trim();
    let resolved = resolve_icon_url(trimmed)?;

    let no_explicit_path = if let Some(rest) = trimmed.strip_prefix("https://") {
        !rest.contains('/')
    } else {
        !trimmed.contains("://") && !trimmed.contains('/')
    };

    if !no_explicit_path {
        return Some(resolved);
    }

    let mut url = reqwest::Url::parse(&resolved).ok()?;
    url.set_path(BCMR_WELL_KNOWN_PATH);
    Some(url.to_string())
}

'''
s = replace_once(s, fetch_doc, resolver + fetch_doc, "resolver insertion")

s = replace_once(
    s,
    'let url = match resolve_icon_url(uri) {',
    'let url = match resolve_bcmr_uri(uri) {',
    "fetch callsite",
)

test_anchor = '    #[test]\n    fn body_archive_routes_by_verification_and_size() {'
regression = '''    #[test]
    fn resolves_bcmr_publication_uris() {
        let well_known =
            "https://example.com/.well-known/bitcoin-cash-metadata-registry.json";

        assert_eq!(resolve_bcmr_uri("example.com").as_deref(), Some(well_known));
        assert_eq!(
            resolve_bcmr_uri("https://example.com").as_deref(),
            Some(well_known)
        );

        assert_eq!(
            resolve_bcmr_uri("example.com/").as_deref(),
            Some("https://example.com/")
        );
        assert_eq!(
            resolve_bcmr_uri("https://example.com/").as_deref(),
            Some("https://example.com/")
        );

        assert_eq!(
            resolve_bcmr_uri("example.com/registry.json").as_deref(),
            Some("https://example.com/registry.json")
        );
        assert_eq!(
            resolve_bcmr_uri("https://example.com/registry.json").as_deref(),
            Some("https://example.com/registry.json")
        );

        for uri in ["ipfs://bafytest", "http://example.com/registry.json"] {
            assert_eq!(resolve_bcmr_uri(uri), resolve_icon_url(uri));
        }
    }

'''
s = replace_once(s, test_anchor, regression + test_anchor, "test insertion")

path.write_text(s, encoding="utf-8")
