import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { getColor } from "../../utils/colorPalette";
import useAppStore from "../../store/useAppStore";

// Kat yüksekliği (metre)
const STORY_HEIGHT = 3.0;
// Kesit boyutları (görsel)
const BEAM_SECTION = 0.3;
const COL_SECTION = 0.3;

export default function IFCScene({ onElementClick }) {
  const mountRef = useRef();
  const sceneRef = useRef();
  const cameraRef = useRef();
  const rendererRef = useRef();
  const meshesRef = useRef([]);
  const targetRef = useRef(new THREE.Vector3(5, 4.5, 5));

  const { ifcFile, elements, statusFilter, activeStory } = useAppStore();
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const mount = mountRef.current;
    const width = mount.clientWidth;
    const height = mount.clientHeight;

    // Scene
    const scene = new THREE.Scene();
    scene.background = new THREE.Color("#080b10");
    sceneRef.current = scene;

    // Camera
    const camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 1000);
    cameraRef.current = camera;

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(window.devicePixelRatio);
    mount.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // Lights
    const ambient = new THREE.AmbientLight(0xffffff, 0.6);
    scene.add(ambient);
    const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
    dirLight.position.set(20, 30, 20);
    scene.add(dirLight);

    // Grid
    const grid = new THREE.GridHelper(50, 50, "#1e2738", "#1e2738");
    scene.add(grid);

    // Orbit controls (manual)
    let isMouseDown = false;
    let rightMouseDown = false;
    let lastMouse = { x: 0, y: 0 };
    let spherical = { theta: Math.PI / 4, phi: Math.PI / 3, radius: 30 };

    const updateCamera = () => {
      const target = targetRef.current;
      camera.position.x = target.x + spherical.radius * Math.sin(spherical.phi) * Math.sin(spherical.theta);
      camera.position.y = target.y + spherical.radius * Math.cos(spherical.phi);
      camera.position.z = target.z + spherical.radius * Math.sin(spherical.phi) * Math.cos(spherical.theta);
      camera.lookAt(target);
    };
    updateCamera();

    const onMouseDown = (e) => {
      if (e.button === 2) {
        rightMouseDown = true;
      } else {
        isMouseDown = true;
      }
      lastMouse = { x: e.clientX, y: e.clientY };
    };
    const onMouseUp = () => { isMouseDown = false; rightMouseDown = false; };
    const onMouseMove = (e) => {
      const dx = e.clientX - lastMouse.x;
      const dy = e.clientY - lastMouse.y;
      lastMouse = { x: e.clientX, y: e.clientY };

      if (isMouseDown) {
        // Orbit
        spherical.theta -= dx * 0.005;
        spherical.phi = Math.max(0.1, Math.min(Math.PI - 0.1, spherical.phi + dy * 0.005));
        updateCamera();
      } else if (rightMouseDown) {
        // Pan
        const panSpeed = 0.03;
        const right = new THREE.Vector3();
        const up = new THREE.Vector3(0, 1, 0);
        camera.getWorldDirection(right);
        right.cross(up).normalize();
        targetRef.current.addScaledVector(right, -dx * panSpeed);
        targetRef.current.y += dy * panSpeed;
        updateCamera();
      }
    };
    const onWheel = (e) => {
      spherical.radius = Math.max(3, Math.min(150, spherical.radius + e.deltaY * 0.05));
      updateCamera();
    };
    const onContextMenu = (e) => e.preventDefault();

    mount.addEventListener("mousedown", onMouseDown);
    mount.addEventListener("mouseup", onMouseUp);
    mount.addEventListener("mousemove", onMouseMove);
    mount.addEventListener("wheel", onWheel);
    mount.addEventListener("contextmenu", onContextMenu);

    // Click — raycasting (sadece kısa click, drag değil)
    let mouseDownPos = { x: 0, y: 0 };
    const onClickDown = (e) => { mouseDownPos = { x: e.clientX, y: e.clientY }; };
    const onClickUp = (e) => {
      const dist = Math.hypot(e.clientX - mouseDownPos.x, e.clientY - mouseDownPos.y);
      if (dist > 5) return; // drag ise click sayma

      const rect = mount.getBoundingClientRect();
      const mouse = new THREE.Vector2(
        ((e.clientX - rect.left) / rect.width) * 2 - 1,
        -((e.clientY - rect.top) / rect.height) * 2 + 1
      );
      const raycaster = new THREE.Raycaster();
      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(meshesRef.current);
      if (intersects.length > 0) {
        const mesh = intersects[0].object;
        onElementClick && onElementClick(mesh.userData.elementId);
      }
    };
    mount.addEventListener("mousedown", onClickDown);
    mount.addEventListener("mouseup", onClickUp);

    // Animate
    let animId;
    const animate = () => {
      animId = requestAnimationFrame(animate);
      renderer.render(scene, camera);
    };
    animate();

    // Resize
    const onResize = () => {
      const w = mount.clientWidth;
      const h = mount.clientHeight;
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
      mount.removeEventListener("contextmenu", onContextMenu);
      mount.removeEventListener("mousedown", onClickDown);
      mount.removeEventListener("mouseup", onClickUp);
      window.removeEventListener("resize", onResize);
      mount.removeChild(renderer.domElement);
      renderer.dispose();
    };
  }, []);

  // Elemanları sahneye ekle
  useEffect(() => {
    if (!sceneRef.current || elements.length === 0) return;

    // Önceki mesh'leri temizle
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

    // Bounding box hesapla (kamera hedefi için)
    let minX = Infinity, maxX = -Infinity;
    let minY = Infinity, maxY = -Infinity;
    let minZ = Infinity, maxZ = -Infinity;

    filtered.forEach((el) => {
      const color = getColor(el.status);
      const isBeam = el.ifc_type === "IfcBeam";

      const material = new THREE.MeshLambertMaterial({
        color: new THREE.Color(color),
        transparent: true,
        opacity: 0.85,
      });

      let mesh;

      if (isBeam) {
        // ---- KİRİŞ ----
        // pi ve pj noktalarından gerçek uzunluk ve yön hesapla
        const pi_x = el.pi_x ?? el.x ?? 0;
        const pi_y = el.pi_y ?? el.y ?? 0;
        const pj_x = el.pj_x ?? (el.x ?? 0) + 1;
        const pj_y = el.pj_y ?? el.y ?? 0;
        const elev = (el.z ?? 0) + STORY_HEIGHT; // kiriş kat üstünde

        const dx = pj_x - pi_x;
        const dy = pj_y - pi_y;
        const length = Math.sqrt(dx * dx + dy * dy);
        const realLength = Math.max(length, 0.5);

        // Kiriş geometrisi — uzunluk X ekseninde
        const geometry = new THREE.BoxGeometry(realLength, BEAM_SECTION, BEAM_SECTION);
        mesh = new THREE.Mesh(geometry, material);

        // Orta noktaya yerleştir
        //   Three.js: X → sağ, Y → yukarı, Z → ekrana doğru
        //   Yapı:     X → X,   Y → Z (derinlik), Z (elev) → Y (yukarı)
        const midX = (pi_x + pj_x) / 2;
        const midY = (pi_y + pj_y) / 2;
        mesh.position.set(midX, elev, midY);

        // Y ekseni etrafında döndür (plan görünümünde açı)
        const angle = Math.atan2(dy, dx);
        mesh.rotation.y = -angle;

        // Bounding box güncelle
        minX = Math.min(minX, pi_x, pj_x);
        maxX = Math.max(maxX, pi_x, pj_x);
        minZ = Math.min(minZ, pi_y, pj_y);
        maxZ = Math.max(maxZ, pi_y, pj_y);
        minY = Math.min(minY, elev);
        maxY = Math.max(maxY, elev);
      } else {
        // ---- KOLON ----
        const cx = el.x ?? 0;
        const cy = el.y ?? 0;
        const baseElev = el.z ?? 0;

        const geometry = new THREE.BoxGeometry(COL_SECTION, STORY_HEIGHT, COL_SECTION);
        mesh = new THREE.Mesh(geometry, material);

        // Kolon tabanından kat yüksekliğine kadar
        // BoxGeometry merkez orijinli, yarı yükseklik kaydır
        mesh.position.set(cx, baseElev + STORY_HEIGHT / 2, cy);

        // Bounding box güncelle
        minX = Math.min(minX, cx);
        maxX = Math.max(maxX, cx);
        minZ = Math.min(minZ, cy);
        maxZ = Math.max(maxZ, cy);
        minY = Math.min(minY, baseElev);
        maxY = Math.max(maxY, baseElev + STORY_HEIGHT);
      }

      mesh.userData.elementId = el.ifc_global_id;
      sceneRef.current.add(mesh);
      meshesRef.current.push(mesh);
    });

    // Kamerayı modelin merkezine yönlendir
    if (filtered.length > 0 && isFinite(minX)) {
      const cx = (minX + maxX) / 2;
      const cy = (minY + maxY) / 2;
      const cz = (minZ + maxZ) / 2;
      targetRef.current.set(cx, cy, cz);

      // Kamerayı güncelle
      if (cameraRef.current) {
        const span = Math.max(maxX - minX, maxY - minY, maxZ - minZ, 10);
        const cam = cameraRef.current;
        cam.position.set(cx + span, cy + span * 0.7, cz + span);
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
