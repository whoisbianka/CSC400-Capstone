# Explore preferences and starting over

The preferences form has moved out of chat. The chat links recommended majors to
Explore, where saved program preferences are applied on entry.

## Explore controls

Both Programs and Majors have:
- Apply filters: changes the current search without saving defaults.
- Save my preferences: saves every current filter and the sort for that tab,
  then shows the matching results from page 1.
- Reset preferences: clears saved preferences for both tabs and resets the view.
- Clear filters: clears only the current search, leaving saved defaults alone.

Explicit filtered URLs and pagination take precedence over saved defaults. A link
from a chat recommendation keeps its major restriction while applying saved
location, degree, budget and other program filters. Saved favorite-major filters
are intersected with current favorites when restored.

## Storage

Signed-in users save state, city, maximum net price, and degree levels in existing
`user_info.search_state`, `search_city`, `max_cost`, and `degree_level` columns.
The supplied TEXT degree_level stores `2`, `3`, `2,3`, or NULL for unrestricted.
Other profile fields are preserved when saving these controls.

All additional Explore controls (including major searches, selected favorites,
school search, tuition limits, acceptance rates, and sorts) are stored in the
signed Flask session, scoped to the account. These additional settings last for
the session rather than across devices/logins, because there are no corresponding
columns in user_info. No additional database schema fields were added.

Guests store the complete per-tab settings in guest_sessions.state.explore_preferences
using the existing version and expiration checks. Preferences are not migrated on
sign-in. Reset preferences deletes only the user's profile row and the saved
Explore settings, or clears the guest preference state. Chat and favorites remain.

## Reset chat and recommendations

The chat page has a separate confirmation-protected reset button. For accounts,
one transaction deletes the user's chatlog, user_keywords, major_rec, and
program_rec records. Major/program favorites, user_info, and the account remain.
For guests, messages, keywords, and recommendations are cleared while preferences
are retained. A stale guest write returns a conflict instead of overwriting newer
state. The browser disables reset during its own active chat request.

Routes: POST /api/explore/preferences and POST /api/chat/reset. Both require CSRF
and derive identity from the Flask session. The old /api/chat/preferences form/API
has been removed. Gemini directs preference changes to Explore instead.

The code expects the degree_level column you added to exist in the database.
No db_setup run or cloud database modification was performed by the assistant.

## Prototype UI integration

The working app uses the prototype's palette, shared page styles and homepage
layout while retaining its existing authentication/favorites/reset functionality.
The prototype directory is reference-only and was not edited. Explore text and numeric fields are always enabled; blank fields apply no
restriction, and zero remains a valid numeric filter. The Has programs control
has been removed. All collapsible sections start closed even with saved filters.
The Majors section shows name search and signed-in users’ favorite checkboxes
together; results include the named major or any checked favorite.
Favorites cards include statistics and descriptions using the existing comparison
queries; Explore’s favorite-state requests still use the lightweight endpoints.
If optional preference loading fails, Explore
continues with the current visible filters rather than refusing access.
