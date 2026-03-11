import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { getColor } from "../../utils/colorPalette";
import useAppStore from "../../store/useAppStore";

export default function IFCScene({ onElementClick }) {
  const mountRef = useRef();
  const sceneRef = useRef();
  const cameraRef = useRef();
  const rendererRef = useRef();
  const meshesRef = useRef([]);

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
    camera.position.set(5, 15, 25);
    camera.lookAt(5, 5, 5);
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
    dirLight.position.set(10, 20, 10);
    scene.add(dirLight);

    // Grid
    const grid = new THREE.GridHelper(50, 50, "#1e2738", "#1e2738");
    scene.add(grid);

    // Orbit controls (manual)
    let isMouseDown = false;
    let lastMouse = { x: 0, y: 0 };
    let spherical = { theta: Math.PI / 4, phi: Math.PI / 3, radius: 20 };

    const updateCamera = () => {
      camera.position.x = spherical.radius * Math.sin(spherical.phi) * Math.sin(spherical.theta);
      camera.position.y = spherical.radius * Math.cos(spherical.phi);
      camera.position.z = spherical.radius * Math.sin(spherical.phi) * Math.cos(spherical.theta);
      camera.lookAt(5, 5, 5);
    };
    updateCamera();

    const onMouseDown = (e) => { isMouseDown = true; lastMouse = { x: e.clientX, y: e.clientY }; };
    const onMouseUp = () => { isMouseDown = false; };
    const onMouseMove = (e) => {
      if (!isMouseDown) return;
      const dx = e.clientX - lastMouse.x;
      const dy = e.clientY - lastMouse.y;
      spherical.theta -= dx * 0.005;
      spherical.phi = Math.max(0.1, Math.min(Math.PI - 0.1, spherical.phi + dy * 0.005));
      lastMouse = { x: e.clientX, y: e.clientY };
      updateCamera();
    };
    const onWheel = (e) => {
      spherical.radius = Math.max(3, Math.min(100, spherical.radius + e.deltaY * 0.05));
      updateCamera();
    };

    mount.addEventListener("mousedown", onMouseDown);
    mount.addEventListener("mouseup", onMouseUp);
    mount.addEventListener("mousemove", onMouseMove);
    mount.addEventListener("wheel", onWheel);

    // Click — raycasting
    const onMouseClick = (e) => {
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
    mount.addEventListener("click", onMouseClick);

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
      mount.removeEventListener("click", onMouseClick);
      window.removeEventListener("resize", onResize);
      mount.removeChild(renderer.domElement);
      renderer.dispose();
    };
  }, []);

  // Elemanları sahneye ekle
  useEffect(() => {
    if (!sceneRef.current || elements.length === 0) return;

    // Önceki mesh'leri temizle
    meshesRef.current.forEach((m) => sceneRef.current.remove(m));
    meshesRef.current = [];

    const filtered = elements.filter((el) => {
      const statusOk = statusFilter.includes(el.status);
      const storyOk = activeStory === "ALL" || el.ifc_story === activeStory;
      return statusOk && storyOk;
    });

    filtered.forEach((el, i) => {
      const color = getColor(el.status);
      const isBeam = el.ifc_type === "IfcBeam";
      const geometry = isBeam
        ? new THREE.BoxGeometry(2, 0.4, 0.4)   // yatay kiriş
        : new THREE.BoxGeometry(0.4, 2, 0.4);  // dikey kolon
      const material = new THREE.MeshLambertMaterial({
        color: new THREE.Color(color),
        transparent: true,
        opacity: 0.85,
      });
      const mesh = new THREE.Mesh(geometry, material);

      // Kirişi doğru yöne döndür
      if (isBeam) {
        const dx = (el.pj_x ?? 1) - (el.pi_x ?? 0);
        const dy = (el.pj_y ?? 0) - (el.pi_y ?? 0);
        mesh.rotation.y = -Math.atan2(dy, dx);
      }

      // Gerçek koordinatları kullan
      const x = (el.x ?? 0);
      const z = (el.y ?? 0);
      const y = (el.z ?? 0) + 1.5;
      mesh.position.set(x, z + 1, y);

      mesh.userData.elementId = el.ifc_global_id;
      sceneRef.current.add(mesh);
      meshesRef.current.push(mesh);
    });
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