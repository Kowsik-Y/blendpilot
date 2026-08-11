"use client";

import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Box, Layers, RotateCw, Sparkles } from "lucide-react";

export interface WorkflowSceneObject {
  name: string;
  primitiveType: string;
  dimensions: [number, number, number];
  location: [number, number, number];
  rotation?: [number, number, number];
  materialName?: string;
  modifiers?: string[];
}

interface ThreeViewportProps {
  assetSpec?: {
    asset_type?: string;
    dimensions?: { width: number; depth: number; height: number };
  };
  sceneObjects?: WorkflowSceneObject[];
  wireframeMode?: boolean;
  selectedObjectName?: string | null;
  onObjectSelect?: (name: string | null) => void;
}

function createGeometry(object: WorkflowSceneObject) {
  const [w, d, h] = object.dimensions;
  const type = object.primitiveType;

  if (type === "cylinder") return new THREE.CylinderGeometry(w / 2, d / 2, h, 32);
  if (type === "uv_sphere") return new THREE.SphereGeometry(Math.max(w, d, h) / 2, 32, 16);
  if (type === "ico_sphere") return new THREE.IcosahedronGeometry(Math.max(w, d, h) / 2, 2);
  if (type === "cone") return new THREE.ConeGeometry(Math.max(w, d) / 2, h, 32);
  if (type === "torus") return new THREE.TorusGeometry(Math.max(w, d) / 2, Math.max(0.01, h / 2), 16, 48);
  if (type === "plane") return new THREE.PlaneGeometry(w, d);
  return new THREE.BoxGeometry(w, h, d);
}

function createMaterial(object: WorkflowSceneObject, wireframe: boolean, selected: boolean) {
  const isAccent = /accent|strip|core|emissive|glow/i.test(object.name + object.materialName);
  const isMetal = /metal|hoop|bevel|dark/i.test(object.name + object.materialName);
  const isWood = /wood|barrel|table|leg/i.test(object.name + object.materialName);

  return new THREE.MeshStandardMaterial({
    color: selected ? 0x38bdf8 : isAccent ? 0x06b6d4 : isWood ? 0x8b5a2b : isMetal ? 0x1f2937 : 0x334155,
    metalness: selected || isMetal || isAccent ? 0.78 : 0.2,
    roughness: isWood ? 0.65 : selected ? 0.25 : 0.35,
    emissive: selected ? 0x0f172a : isAccent ? 0x06b6d4 : 0x000000,
    emissiveIntensity: selected ? 0.4 : isAccent ? 1.6 : 0,
    wireframe,
  });
}

function addEdges(mesh: THREE.Mesh) {
  const edges = new THREE.EdgesGeometry(mesh.geometry, 25);
  const line = new THREE.LineSegments(
    edges,
    new THREE.LineBasicMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.35 })
  );
  mesh.add(line);
}

export function ThreeViewport({
  assetSpec,
  sceneObjects = [],
  wireframeMode = false,
  selectedObjectName = null,
  onObjectSelect,
}: ThreeViewportProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const meshGroupRef = useRef<THREE.Group | null>(null);
  const autoRotateRef = useRef(false);

  const [wireframe, setWireframe] = useState(false);
  const [autoRotate, setAutoRotate] = useState(false);
  const [cameraView, setCameraView] = useState<"iso" | "front" | "top">("iso");
  const effectiveWireframe = wireframe || wireframeMode;

  useEffect(() => {
    autoRotateRef.current = autoRotate;
  }, [autoRotate]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xffffff);
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(
      45,
      container.clientWidth / container.clientHeight,
      0.1,
      100
    );
    camera.position.set(2.4, 2.0, 3.2);
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "high-performance" });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.15;
    rendererRef.current = renderer;

    container.innerHTML = "";
    container.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.target.set(0, 0.4, 0);
    controls.maxPolarAngle = Math.PI / 2 + 0.05;
    controls.minDistance = 0.5;
    controls.maxDistance = 15;
    controlsRef.current = controls;

    scene.add(new THREE.AmbientLight(0xffffff, 0.6));

    const keyLight = new THREE.DirectionalLight(0xffffff, 1.8);
    keyLight.position.set(4, 8, 5);
    keyLight.castShadow = true;
    keyLight.shadow.mapSize.width = 2048;
    keyLight.shadow.mapSize.height = 2048;
    keyLight.shadow.bias = -0.0001;
    scene.add(keyLight);

    const fillLight = new THREE.DirectionalLight(0x06b6d4, 1.0);
    fillLight.position.set(-5, 3, -4);
    scene.add(fillLight);

    const rimLight = new THREE.DirectionalLight(0xa855f7, 1.2);
    rimLight.position.set(0, 5, -6);
    scene.add(rimLight);

    const gridHelper = new THREE.GridHelper(10, 20, 0x0ea5e9, 0xe2e8f0);
    scene.add(gridHelper);

    const floor = new THREE.Mesh(
      new THREE.PlaneGeometry(20, 20),
      new THREE.ShadowMaterial({ opacity: 0.18 })
    );
    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    scene.add(floor);

    let animationFrameId: number;
    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      controls.update();
      if (autoRotateRef.current && meshGroupRef.current) {
        meshGroupRef.current.rotation.y += 0.004;
      }
      renderer.render(scene, camera);
    };
    animate();

    const resizeObserver = new ResizeObserver(() => {
      const w = container.clientWidth;
      const h = container.clientHeight;
      if (w === 0 || h === 0) return;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    });
    resizeObserver.observe(container);

    return () => {
      cancelAnimationFrame(animationFrameId);
      resizeObserver.disconnect();
      renderer.dispose();
      scene.traverse((object) => {
        if (object instanceof THREE.Mesh) {
          object.geometry.dispose();
          if (Array.isArray(object.material)) {
            object.material.forEach((material) => material.dispose());
          } else {
            object.material.dispose();
          }
        }
      });
    };
  }, [onObjectSelect]);

  useEffect(() => {
    const scene = sceneRef.current;
    const renderer = rendererRef.current;
    const camera = cameraRef.current;
    if (!scene) return;

    if (meshGroupRef.current) {
      scene.remove(meshGroupRef.current);
      meshGroupRef.current.traverse((object) => {
        if (object instanceof THREE.Mesh) {
          object.geometry.dispose();
          if (Array.isArray(object.material)) {
            object.material.forEach((material) => material.dispose());
          } else {
            object.material.dispose();
          }
        }
      });
    }

    const group = new THREE.Group();
    sceneObjects.forEach((object) => {
      const selected = object.name === selectedObjectName;
      const mesh = new THREE.Mesh(
        createGeometry(object),
        createMaterial(object, effectiveWireframe, selected)
      );
      const [x, y, z] = object.location;
      mesh.position.set(x, z, y);
      if (object.rotation) {
        const [rx, ry, rz] = object.rotation;
        mesh.rotation.set(rx, rz, ry);
      }
      if (object.primitiveType === "torus") {
        mesh.rotation.x = Math.PI / 2;
      }
      mesh.name = object.name;
      mesh.userData = { objectName: object.name };
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      addEdges(mesh);
      if (selected) {
        mesh.scale.setScalar(1.02);
      }
      group.add(mesh);
    });

    scene.add(group);
    meshGroupRef.current = group;

    if (renderer && camera) {
      const raycaster = new THREE.Raycaster();
      const pointer = new THREE.Vector2();
      const handlePointerDown = (event: PointerEvent) => {
        const rect = renderer.domElement.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) return;

        pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        pointer.y = -(((event.clientY - rect.top) / rect.height) * 2 - 1);
        raycaster.setFromCamera(pointer, camera);

        const intersections = raycaster.intersectObjects(group.children, true);
        const hit = intersections.find((intersection) => intersection.object instanceof THREE.Mesh)?.object;
        onObjectSelect?.(hit?.name || null);
      };

      renderer.domElement.addEventListener("pointerdown", handlePointerDown);
      return () => {
        renderer.domElement.removeEventListener("pointerdown", handlePointerDown);
      };
    }
  }, [sceneObjects, effectiveWireframe, selectedObjectName, onObjectSelect]);

  const handleSetView = (view: "iso" | "front" | "top") => {
    setCameraView(view);
    if (!cameraRef.current || !controlsRef.current) return;

    if (view === "iso") {
      cameraRef.current.position.set(2.4, 2.0, 3.2);
      controlsRef.current.target.set(0, 0.4, 0);
    } else if (view === "front") {
      cameraRef.current.position.set(0, 0.6, 4.0);
      controlsRef.current.target.set(0, 0.5, 0);
    } else {
      cameraRef.current.position.set(0, 4.5, 0.01);
      controlsRef.current.target.set(0, 0, 0);
    }
    controlsRef.current.update();
  };

  return (
    <div className="relative w-full h-full min-h-120 rounded-2xl overflow-hidden border border-border bg-card shadow-2xl flex flex-col">
      <div className="absolute top-4 left-4 right-4 z-10 flex items-center justify-between pointer-events-none">
        <div className="flex items-center gap-2 pointer-events-auto">
          <Badge variant="outline" className="bg-background/85 backdrop-blur-md border-cyan-500/40 text-cyan-300 text-xs px-2.5 py-1 font-semibold">
            <Box className="w-3.5 h-3.5 mr-1 text-cyan-400" />
            {assetSpec?.asset_type ? assetSpec.asset_type.toUpperCase() : "READY"}
          </Badge>
          <Badge variant="outline" className="bg-background/75 backdrop-blur-md text-xs text-muted-foreground font-mono">
            {sceneObjects.length} live objects
          </Badge>
        </div>

        <div className="flex items-center gap-1 pointer-events-auto bg-background/85 backdrop-blur-md p-1 rounded-xl border border-border shadow-lg">
          <div className="flex bg-muted/40 p-0.5 rounded-lg mr-1">
            <button
              onClick={() => handleSetView("iso")}
              className={`text-[11px] px-2 py-0.5 rounded-md transition-colors ${cameraView === "iso" ? "bg-card text-foreground font-medium" : "text-muted-foreground hover:text-foreground"}`}
            >
              Iso
            </button>
            <button
              onClick={() => handleSetView("front")}
              className={`text-[11px] px-2 py-0.5 rounded-md transition-colors ${cameraView === "front" ? "bg-card text-foreground font-medium" : "text-muted-foreground hover:text-foreground"}`}
            >
              Front
            </button>
            <button
              onClick={() => handleSetView("top")}
              className={`text-[11px] px-2 py-0.5 rounded-md transition-colors ${cameraView === "top" ? "bg-card text-foreground font-medium" : "text-muted-foreground hover:text-foreground"}`}
            >
              Top
            </button>
          </div>

          <Button
            size="sm"
            variant="ghost"
            className={`h-7 px-2 text-xs ${effectiveWireframe ? "text-cyan-400 bg-cyan-500/10" : "text-muted-foreground"}`}
            onClick={() => setWireframe((prev) => !prev)}
            title="Toggle Wireframe Overlay"
          >
            <Layers className="w-3.5 h-3.5 mr-1" />
            Wireframe
          </Button>

          <Button
            size="sm"
            variant="ghost"
            className={`h-7 px-2 text-xs ${autoRotate ? "text-primary bg-primary/10" : "text-muted-foreground"}`}
            onClick={() => setAutoRotate((prev) => !prev)}
            title="Toggle Turntable Rotation"
          >
            <RotateCw className="w-3.5 h-3.5 mr-1" />
            Turntable
          </Button>
        </div>
      </div>

      {sceneObjects.length === 0 && (
        <div className="absolute inset-x-0 top-20 z-10 flex justify-center pointer-events-none">
          <Badge variant="outline" className="bg-background/85 text-muted-foreground">
            Waiting for agent-created geometry
          </Badge>
        </div>
      )}

      <div ref={containerRef} className="w-full flex-1 min-h-110 cursor-grab active:cursor-grabbing" />

      <div className="px-4 py-2 bg-card/70 backdrop-blur-md border-t border-border flex items-center justify-between text-[11px] text-muted-foreground">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5 text-foreground font-medium">
            <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
            Live WebSocket Scene Preview
          </span>
          <span>•</span>
          <span>No static model generation</span>
        </div>
        <span className="font-mono text-[10px] text-muted-foreground/60">WebGL 2.0</span>
      </div>
    </div>
  );
}
