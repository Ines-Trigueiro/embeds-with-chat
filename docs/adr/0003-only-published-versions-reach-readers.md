# Versions are immutable and only explicitly published versions reach readers

Every model reply that contains HTML creates a new immutable version, with its dataset already injected. Readers can only reach versions the journalist has explicitly published, and publishing is gated by the quality check. A snippet either follows the latest published version or is pinned to one with `data-version`. Unpublished versions return 404 on the embed origin. We rejected a single mutable document per embed, because it would let a half-finished edit, or an edit that never passed the quality check, reach readers of an article that is already live.

## Amendment: signed preview URLs

The journalist's preview has to load unpublished versions from the embed origin, under the same sandbox and CSP readers get. Rendering them on the editor origin instead would weaken ADR 0001. So the embed origin serves any version through a preview URL signed with a secret both origins share. The signature covers the embed, the version number and an expiry (24 hours by default). A preview URL that leaks, for example one pasted into an article by mistake, stops working, and it can never be turned into a different version or a later expiry. Without a valid, unexpired signature the embed origin returns 404, as above. This is the only way a version that isn't published can be reached.
