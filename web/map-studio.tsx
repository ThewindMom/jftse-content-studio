import { createRoot } from "react-dom/client";
import { TwinkleStudio } from "./TwinkleStudio.tsx";

function MapLibrary() {
  return <main className="tw-studio tw-map-library">
    <header className="tw-header"><a className="tw-brand" href="/"><span>FT</span> CONTENT STUDIO</a><span className="tw-pill">MAP DESIGN</span></header>
    <section className="tw-map-collection">
      <p className="tw-eyebrow">YOUR WORKSPACE</p><h1>Choose a map design</h1>
      <p className="tw-map-intro">Start with the original town, or continue the Oktoberfest composition. Each design keeps its own saved layout.</p>
      <div className="tw-map-cards">
        <a className="tw-map-card" href="/map-studio?map=twinkle"><span className="tw-map-number">01 / BASELINE</span><h2>Twinkle Town</h2><p>The original square, fountain and court. Stock characters and carts are visible in rest pose, ready to reposition.</p><ul><li>Original stock placements</li><li>Scenery, characters and festival prop library</li><li>Independent saved layout</li></ul><strong>Open Twinkle Town <span aria-hidden="true">↗</span></strong></a>
        <a className="tw-map-card tw-festival-card" href="/map-studio?map=oktoberfest"><span className="tw-map-number">02 / AUTHORED VARIATION</span><h2>Oktoberfest</h2><p>A brewers’ pavilion, three food carts, conversations and gathering places around the playable court.</p><ul><li>30 authored placements + retained residents</li><li>Four masked stage-material edits</li><li>Separate save · dependency-inclusive export</li></ul><strong>Open Oktoberfest <span aria-hidden="true">↗</span></strong></a>
      </div>
      <aside className="tw-map-note"><h2>A design is not a new game map ID</h2><p>Both designs export as replacements for Twinkle Town (map 2) in a separate test client. The Studio never installs them. Rest-pose previews do not simulate animation, effects or gameplay.</p><p>Oktoberfest requires the private authored resource folder configured on the server. Your stock resources remain untouched.</p></aside>
    </section>
  </main>;
}

const root = document.getElementById("map-studio-root");
const map = new URLSearchParams(location.search).get("map");
if (root) createRoot(root).render(map === "twinkle" || map === "oktoberfest" ? <TwinkleStudio mapId={map} /> : <MapLibrary />);
