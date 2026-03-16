import { useEffect, useRef, useState, useCallback } from "react";
import * as THREE from "three";
import useAppStore from "../../store/useAppStore";

const STORY_HEIGHT = 3.0;
const DEFAULT_SECTION = 0.3;
const HOVER_EMISSIVE = 0.35;

// ─── Sonsuz Grid (shader) ───
function createInfiniteGrid() {
  const geo = new THREE.PlaneGeometry(2, 2);
  const mat = new THREE.ShaderMaterial({
    side: THREE.DoubleSide, transparent: true, depthWrite: false,
    uniforms: { uColor: { value: new THREE.Color("#1e2738") }, uFade: { value: 150.0 } },
    vertexShader: `varying vec3 vWP; void main(){ vec4 w=modelMatrix*vec4(position,1.); vWP=w.xyz; gl_Position=projectionMatrix*viewMatrix*w; }`,
    fragmentShader: `uniform vec3 uColor; uniform float uFade; varying vec3 vWP;
      void main(){ vec2 c=vWP.xz; vec2 g=abs(fract(c-0.5)-0.5)/fwidth(c); float l=min(g.x,g.y);
      float a=1.0-min(l,1.0); a*=max(0.0,1.0-length(vWP.xz)/uFade); gl_FragColor=vec4(uColor,a*0.5); }`,
  });
  const m = new THREE.Mesh(geo, mat);
  m.rotation.x = -Math.PI / 2;
  m.scale.set(10000, 10000, 1);
  m.frustumCulled = false;
  m.userData._isGrid = true;
  return m;
}

// ─── Outline Efekti (scale-up wireframe) ───
function createOutline(mesh, color = "#ffffff") {
  const geo = mesh.geometry.clone();
  const mat = new THREE.MeshBasicMaterial({
    color: new THREE.Color(color),
    wireframe: true,
    transparent: true,
    opacity: 0.6,
  });
  const outline = new THREE.Mesh(geo, mat);
  outline.position.copy(mesh.position);
  outline.rotation.copy(mesh.rotation);
  outline.scale.copy(mesh.scale).multiplyScalar(1.04);
  outline.userData._isOutline = true;
  return outline;
}

export default function IFCScene({ onElementClick, viewMode = "solid" }) {
  const mountRef = useRef();
  const sceneRef = useRef();
  const cameraRef = useRef();
  const rendererRef = useRef();
  const meshesRef = useRef([]);
  const outlineRef = useRef(null);
  const hoveredRef = useRef(null);
  const targetRef = useRef(new THREE.Vector3(5, 4.5, 5));
  const sphericalRef = useRef({ theta: Math.PI / 4, phi: Math.PI / 3, radius: 30 });

  const { elements, statusFilter, activeStory, bgColor, statusColors, selectedElement } = useAppStore();
  const [loading, setLoading] = useState(false);
  const [tooltip, setTooltip] = useState(null);

  // Ekran görüntüsü fonksiyonu
  const takeScreenshot = useCallback(() => {
    if (!rendererRef.current || !sceneRef.current || !cameraRef.current) return;
    rendererRef.current.render(sceneRef.current, cameraRef.current);
    const url = rendererRef.current.domElement.toDataURL("image/png");
    const a = document.createElement("a");
    a.href = url;
    a.download = "3d_gorunum.png";
    a.click();
  }, []);

  // Expose screenshot to parent
  useEffect(() => {
    if (mountRef.current) mountRef.current._takeScreenshot = takeScreenshot;
  }, [takeScreenshot]);

  // ─── Sahne kurulumu ───
  useEffect(() => {
    const mount = mountRef.current;
    const width = mount.clientWidth;
    const height = mount.clientHeight;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(bgColor);
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 5000);
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(window.devicePixelRatio);
    mount.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    scene.add(new THREE.AmbientLight(0xffffff, 0.6));
    const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
    dirLight.position.set(20, 30, 20);
    scene.add(dirLight);
    scene.add(createInfiniteGrid());

    // ─── Orbit / Pan / Zoom ───
    let isMouseDown = false, rightMouseDown = false;
    let lastMouse = { x: 0, y: 0 };
    const sph = sphericalRef.current;

    const updateCamera = () => {
      const t = targetRef.current;
      camera.position.x = t.x + sph.radius * Math.sin(sph.phi) * Math.sin(sph.theta);
      camera.position.y = t.y + sph.radius * Math.cos(sph.phi);
      camera.position.z = t.z + sph.radius * Math.sin(sph.phi) * Math.cos(sph.theta);
      camera.lookAt(t);
    };
    updateCamera();

    const onMouseDown = (e) => {
      if (e.button === 2) rightMouseDown = true;
      else isMouseDown = true;
      lastMouse = { x: e.clientX, y: e.clientY };
    };
    const onMouseUp = () => { isMouseDown = false; rightMouseDown = false; };
    const onMouseMove = (e) => {
      const dx = e.clientX - lastMouse.x;
      const dy = e.clientY - lastMouse.y;
      lastMouse = { x: e.clientX, y: e.clientY };
      if (isMouseDown) {
        sph.theta -= dx * 0.005;
        sph.phi = Math.max(0.1, Math.min(Math.PI - 0.1, sph.phi + dy * 0.005));
        updateCamera();
      } else if (rightMouseDown) {
        const right = new THREE.Vector3();
        camera.getWorldDirection(right);
        right.cross(new THREE.Vector3(0, 1, 0)).normalize();
        targetRef.current.addScaledVector(right, -dx * 0.03);
        targetRef.current.y += dy * 0.03;
        updateCamera();
      }

      // ─── Hover raycasting ───
      if (!isMouseDown && !rightMouseDown) {
        const rect = mount.getBoundingClientRect();
        const mouse = new THREE.Vector2(
          ((e.clientX - rect.left) / rect.width) * 2 - 1,
          -((e.clientY - rect.top) / rect.height) * 2 + 1
        );
        const ray = new THREE.Raycaster();
        ray.setFromCamera(mouse, camera);
        const hits = ray.intersectObjects(meshesRef.current);

        // Önceki hover'ı temizle
        if (hoveredRef.current) {
          hoveredRef.current.material.emissiveIntensity = 0;
          hoveredRef.current = null;
        }

        if (hits.length > 0) {
          const mesh = hits[0].object;
          mesh.material.emissiveIntensity = HOVER_EMISSIVE;
          hoveredRef.current = mesh;
          mount.style.cursor = "pointer";

          // Tooltip
          const el = elements.find(e => e.ifc_global_id === mesh.userData.elementId);
          if (el) {
            setTooltip({
              x: e.clientX - rect.left + 12,
              y: e.clientY - rect.top - 8,
              name: el.ifc_name,
              type: el.ifc_type === "IfcBeam" ? "Kiriş" : "Kolon",
              story: el.ifc_story,
              status: el.status,
              uc: el.unity_check,
            });
          }
        } else {
          mount.style.cursor = "default";
          setTooltip(null);
        }
      }
    };
    const onWheel = (e) => {
      sph.radius = Math.max(3, Math.min(500, sph.radius + e.deltaY * 0.05));
      updateCamera();
    };
    const onCtx = (e) => e.preventDefault();
    const onMouseLeave = () => {
      if (hoveredRef.current) {
        hoveredRef.current.material.emissiveIntensity = 0;
        hoveredRef.current = null;
      }
      setTooltip(null);
    };

    mount.addEventListener("mousedown", onMouseDown);
    mount.addEventListener("mouseup", onMouseUp);
    mount.addEventListener("mousemove", onMouseMove);
    mount.addEventListener("wheel", onWheel);
    mount.addEventListener("contextmenu", onCtx);
    mount.addEventListener("mouseleave", onMouseLeave);

    // ─── Click ───
    let downPos = { x: 0, y: 0 };
    const onDown2 = (e) => { downPos = { x: e.clientX, y: e.clientY }; };
    const onUp2 = (e) => {
      if (Math.hypot(e.clientX - downPos.x, e.clientY - downPos.y) > 5) return;
      const rect = mount.getBoundingClientRect();
      const mouse = new THREE.Vector2(
        ((e.clientX - rect.left) / rect.width) * 2 - 1,
        -((e.clientY - rect.top) / rect.height) * 2 + 1
      );
      const ray = new THREE.Raycaster();
      ray.setFromCamera(mouse, camera);
      const hits = ray.intersectObjects(meshesRef.current);
      if (hits.length > 0) {
        onElementClick && onElementClick(hits[0].object.userData.elementId);
      }
    };
    mount.addEventListener("mousedown", onDown2);
    mount.addEventListener("mouseup", onUp2);

    let animId;
    const animate = () => { animId = requestAnimationFrame(animate); renderer.render(scene, camera); };
    animate();

    const onResize = () => {
      const w = mount.clientWidth, h = mount.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener("resize", onResize);

    return () => {
      cancelAnimationFrame(animId);
      mount.removeEventListener("mousedown", onMouseDown);
      mount.removeEventListener("mouseup", onMouseUp);
      mount.removeEventListener("mousemove", onMouseMove);
      mount.removeEventListener("wheel", onWheel);
      mount.removeEventListener("contextmenu", onCtx);
      mount.removeEventListener("mouseleave", onMouseLeave);
      mount.removeEventListener("mousedown", onDown2);
      mount.removeEventListener("mouseup", onUp2);
      window.removeEventListener("resize", onResize);
      mount.removeChild(renderer.domElement);
      renderer.dispose();
    };
  }, []);

  // Arka plan rengi değişimi
  useEffect(() => {
    if (sceneRef.current) sceneRef.current.background = new THREE.Color(bgColor);
  }, [bgColor]);

  // ─── Elemanları çiz ───
  useEffect(() => {
    if (!sceneRef.current || elements.length === 0) return;

    // Temizle (outline hariç scene objeleri)
    meshesRef.current.forEach((m) => { sceneRef.current.remove(m); m.geometry.dispose(); m.material.dispose(); });
    meshesRef.current = [];
    if (outlineRef.current) { sceneRef.current.remove(outlineRef.current); outlineRef.current = null; }

    const filtered = elements.filter((el) => {
      return statusFilter.includes(el.status) && (activeStory === "ALL" || el.ifc_story === activeStory);
    });

    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity, minZ = Infinity, maxZ = -Infinity;

    filtered.forEach((el) => {
      const color = statusColors[el.status] || statusColors.UNMATCHED || "#64748b";
      const isBeam = el.ifc_type === "IfcBeam";
      const secDepth = el.sec_depth || DEFAULT_SECTION;
      const secWidth = el.sec_width || DEFAULT_SECTION;

      const isWire = viewMode === "wireframe";
      const isTrans = viewMode === "transparent";

      const material = new THREE.MeshLambertMaterial({
        color: new THREE.Color(color),
        transparent: true,
        opacity: isTrans ? 0.3 : 0.85,
        wireframe: isWire,
        emissive: new THREE.Color(color),
        emissiveIntensity: 0,
      });

      let mesh;

      if (isBeam) {
        const pi_x = el.pi_x ?? el.x ?? 0, pi_y = el.pi_y ?? el.y ?? 0;
        const pj_x = el.pj_x ?? (el.x ?? 0) + 1, pj_y = el.pj_y ?? el.y ?? 0;
        const elev = (el.z ?? 0) + STORY_HEIGHT;
        const dx = pj_x - pi_x, dy = pj_y - pi_y;
        const length = Math.max(Math.sqrt(dx * dx + dy * dy), 0.5);

        mesh = new THREE.Mesh(new THREE.BoxGeometry(length, secDepth, secWidth), material);
        mesh.position.set((pi_x + pj_x) / 2, elev, (pi_y + pj_y) / 2);
        mesh.rotation.y = -Math.atan2(dy, dx);

        minX = Math.min(minX, pi_x, pj_x); maxX = Math.max(maxX, pi_x, pj_x);
        minZ = Math.min(minZ, pi_y, pj_y); maxZ = Math.max(maxZ, pi_y, pj_y);
        minY = Math.min(minY, elev); maxY = Math.max(maxY, elev);
      } else {
        const cx = el.x ?? 0, cy = el.y ?? 0, baseElev = el.z ?? 0;
        mesh = new THREE.Mesh(new THREE.BoxGeometry(secWidth, STORY_HEIGHT, secDepth), material);
        mesh.position.set(cx, baseElev + STORY_HEIGHT / 2, cy);

        minX = Math.min(minX, cx); maxX = Math.max(maxX, cx);
        minZ = Math.min(minZ, cy); maxZ = Math.max(maxZ, cy);
        minY = Math.min(minY, baseElev); maxY = Math.max(maxY, baseElev + STORY_HEIGHT);
      }

      mesh.userData.elementId = el.ifc_global_id;
      sceneRef.current.add(mesh);
      meshesRef.current.push(mesh);
    });

    // Kamera
    if (filtered.length > 0 && isFinite(minX)) {
      const cx = (minX + maxX) / 2, cy = (minY + maxY) / 2, cz = (minZ + maxZ) / 2;
      targetRef.current.set(cx, cy, cz);
      const span = Math.max(maxX - minX, maxY - minY, maxZ - minZ, 10);
      sphericalRef.current.radius = span * 1.5;
      if (cameraRef.current) {
        const cam = cameraRef.current, sph = sphericalRef.current;
        cam.position.set(
          cx + sph.radius * Math.sin(sph.phi) * Math.sin(sph.theta),
          cy + sph.radius * Math.cos(sph.phi),
          cz + sph.radius * Math.sin(sph.phi) * Math.cos(sph.theta)
        );
        cam.lookAt(targetRef.current);
      }
    }
  }, [elements, statusFilter, activeStory, statusColors, viewMode]);

  // ─── Seçili eleman outline ───
  useEffect(() => {
    if (!sceneRef.current) return;
    // Eski outline'ı kaldır
    if (outlineRef.current) {
      sceneRef.current.remove(outlineRef.current);
      outlineRef.current.geometry.dispose();
      outlineRef.current.material.dispose();
      outlineRef.current = null;
    }
    if (!selectedElement) return;

    const mesh = meshesRef.current.find(m => m.userData.elementId === selectedElement);
    if (mesh) {
      const outline = createOutline(mesh, "#5b9cf6");
      sceneRef.current.add(outline);
      outlineRef.current = outline;
    }
  }, [selectedElement]);

  const tooltipColor = tooltip?.status ? (statusColors[tooltip.status] || "#64748b") : "#64748b";

  return (
    <div style={{ position: "relative", width: "100%", height: "100%" }}>
      <div ref={mountRef} style={{ width: "100%", height: "100%" }} />

      {/* Tooltip */}
      {tooltip && (
        <div style={{
          position: "absolute",
          left: tooltip.x, top: tooltip.y,
          background: "#0c1018ee",
          border: `1px solid ${tooltipColor}55`,
          borderRadius: "6px",
          padding: "6px 10px",
          pointerEvents: "none",
          zIndex: 50,
          backdropFilter: "blur(4px)",
          maxWidth: "200px",
        }}>
          <div style={{ fontSize: "12px", fontWeight: "700", color: "#fff", marginBottom: "2px" }}>
            {tooltip.name}
          </div>
          <div style={{ fontSize: "10px", color: "#7090b8" }}>
            {tooltip.type} · {tooltip.story}
          </div>
          {tooltip.uc != null && (
            <div style={{ fontSize: "10px", fontFamily: "monospace", color: tooltipColor, marginTop: "2px" }}>
              UC: {tooltip.uc.toFixed(3)} · %{Math.round(tooltip.uc * 100)}
            </div>
          )}
        </div>
      )}

      {loading && (
        <div style={{
          position: "absolute", inset: 0,
          display: "flex", alignItems: "center", justifyContent: "center",
          background: "#080b10cc", fontSize: "14px", color: "#5b9cf6",
        }}>
          Yükleniyor...
        </div>
      )}
    </div>
  );
}
