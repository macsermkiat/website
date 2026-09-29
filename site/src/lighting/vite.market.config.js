// The site's own Vite config with live reload off, so screenshots of the market are not
// interrupted when teammates save files (used by shoot-market.mjs).
import base from '../../vite.config.js';

export default { ...base, server: { ...(base.server || {}), hmr: false, watch: null } };
