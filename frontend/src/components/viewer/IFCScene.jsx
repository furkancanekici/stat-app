import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { getColor } from "../../utils/colorPalette";
import useAppStore from "../../store/useAppStore";

const STORY_HEIGHT = 3.0;
const DEFAULT_SECTION = 0.3;

export default function IFCScene({ onElementClick }) {
  const mountRef = useRef();
  const sceneRef = useRef();
  const cameraRef = useRef();
  const rendererRef = useRef();
  const meshesRef = useRef([]);
  const targetRef = useRef(new THREE.Vector3(5, 4.5, 5));
  const sphericalRef = useRef({ theta: Math.PI / 4, phi: Math.PI / 3, radius: 30 });

  const { elements, statusFilter, activeStory } = useAppStore();
  const [loading, setLoading] = useState(false);

  // Sahne kurulumu (bir kez)
  useEffect(() => {
    const mount = mountRef.current;
    const width = mount.clientWidth;
    const height = mount.clientHeight;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#080b10");
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 1000);
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(window.devicePixelRatio);
    mount.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    scene.add(new THREE.AmbientLight(0xffffff, 0.6));
    const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
    dirLight.position.set(20, 30, 20);
    scene.add(dirLight);

    scene.add(new THREE.GridHelper(50, 50, "#1e2738", "#1e2738"));

    // Orbit / Pan / Zoom
    let isMouseDown = false;
    let rightMouseDown = false;
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
    };
    const onWheel = (e) => {
      sph.radius = Math.max(3, Math.min(150, sph.radius + e.deltaY * 0.05));
      updateCamera();
    };
    const onCtx = (e) => e.preventDefault();

    mount.addEventListener("mousedown", onMouseDown);
    mount.addEventListener("mouseup", onMouseUp);
    mount.addEventListener("mousemove", onMouseMove);
    mount.addEventListener("wheel", onWheel);
    mount.addEventListener("contextmenu", onCtx);

    // Click (drag ile karışmasın)
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
      mount.removeEventListener("mousedown", onDown2);
      mount.removeEventListener("mouseup", onUp2);
      window.removeEventListener("resize", onResize);
      mount.removeChild(renderer.domElement);
      renderer.dispose();
    };
  }, []);

  // Elemanları çiz
  useEffect(() => {
    if (!sceneRef.current || elements.length === 0) return;

    meshesRef.current.forEach((m) => {
      sceneRef.current.remove(m);
      m.geometry.dispose();
      m.material.dispose();
    });
    meshesRef.current = [];

    const filtered = elements.filter((el) => {
      const statusOk = statusFilter.includes(el.status);
      const storyOk = activeStory === "ALL" || el.ifc_story === activeStory;
      return statusOk && storyOk;
    });

    let minX = Infinity, maxX = -Infinity;
    let minY = Infinity, maxY = -Infinity;
    let minZ = Infinity, maxZ = -Infinity;

    filtered.forEach((el) => {
      const color = getColor(el.status);
      const isBeam = el.ifc_type === "IfcBeam";

      // Gerçek kesit boyutları (backend'den geliyor)
      const secDepth = el.sec_depth || DEFAULT_SECTION;
      const secWidth = el.sec_width || DEFAULT_SECTION;

      const material = new THREE.MeshLambertMaterial({
        color: new THREE.Color(color),
        transparent: true,
        opacity: 0.85,
      });

      let mesh;

      if (isBeam) {
        const pi_x = el.pi_x ?? el.x ?? 0;
        const pi_y = el.pi_y ?? el.y ?? 0;
        const pj_x = el.pj_x ?? (el.x ?? 0) + 1;
        const pj_y = el.pj_y ?? el.y ?? 0;
        const elev = (el.z ?? 0) + STORY_HEIGHT;

        const dx = pj_x - pi_x;
        const dy = pj_y - pi_y;
        const length = Math.max(Math.sqrt(dx * dx + dy * dy), 0.5);

        // Kiriş: uzunluk X, yükseklik(depth) Y, genişlik(width) Z
        const geo = new THREE.BoxGeometry(length, secDepth, secWidth);
        mesh = new THREE.Mesh(geo, material);

        mesh.position.set(
          (pi_x + pj_x) / 2,
          elev,
          (pi_y + pj_y) / 2
        );
        mesh.rotation.y = -Math.atan2(dy, dx);

        minX = Math.min(minX, pi_x, pj_x); maxX = Math.max(maxX, pi_x, pj_x);
        minZ = Math.min(minZ, pi_y, pj_y); maxZ = Math.max(maxZ, pi_y, pj_y);
        minY = Math.min(minY, elev);        maxY = Math.max(maxY, elev);
      } else {
        const cx = el.x ?? 0;
        const cy = el.y ?? 0;
        const baseElev = el.z ?? 0;

        // Kolon: genişlik(width) X, yükseklik(story) Y, derinlik(depth) Z
        const geo = new THREE.BoxGeometry(secWidth, STORY_HEIGHT, secDepth);
        mesh = new THREE.Mesh(geo, material);
        mesh.position.set(cx, baseElev + STORY_HEIGHT / 2, cy);

        minX = Math.min(minX, cx); maxX = Math.max(maxX, cx);
        minZ = Math.min(minZ, cy); maxZ = Math.max(maxZ, cy);
        minY = Math.min(minY, baseElev); maxY = Math.max(maxY, baseElev + STORY_HEIGHT);
      }

      mesh.userData.elementId = el.ifc_global_id;
      sceneRef.current.add(mesh);
      meshesRef.current.push(mesh);
    });

    // Kamerayı modelin merkezine oturt
    if (filtered.length > 0 && isFinite(minX)) {
      const cx = (minX + maxX) / 2;
      const cy = (minY + maxY) / 2;
      const cz = (minZ + maxZ) / 2;
      targetRef.current.set(cx, cy, cz);

      const span = Math.max(maxX - minX, maxY - minY, maxZ - minZ, 10);
      sphericalRef.current.radius = span * 1.5;

      if (cameraRef.current) {
        const cam = cameraRef.current;
        const sph = sphericalRef.current;
        cam.position.set(
          cx + sph.radius * Math.sin(sph.phi) * Math.sin(sph.theta),
          cy + sph.radius * Math.cos(sph.phi),
          cz + sph.radius * Math.sin(sph.phi) * Math.cos(sph.theta)
        );
        cam.lookAt(targetRef.current);
      }
    }
  }, [elements, statusFilter, activeStory]);

  return (
    <div style={{ position: "relative", width: "100%", height: "100%" }}>
      <div ref={mountRef} style={{ width: "100%", height: "100%" }} />
      {loading && (
        <div style={{
          position: "absolute", inset: 0,
          display: "flex", alignItems: "center", justifyContent: "center",
          background: "#080b10cc",
          fontSize: "14px", color: "#5b9cf6",
        }}>
          Yükleniyor...
        </div>
      )}
    </div>
  );
}
