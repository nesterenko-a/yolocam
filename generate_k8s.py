"""
Генерирует Kubernetes-манифесты для yolo-detector.

Использование:
    python generate_k8s.py                          # все манифесты в k8s/
    python generate_k8s.py --domain my.site.com     # с Ingress
    python generate_k8s.py --output ./manifests     # в другую папку
"""

import argparse
import os
from pathlib import Path

import yaml

try:
    from kubernetes.client import (
        ApiClient,
        V1ConfigMap,
        V1ConfigMapEnvSource,
        V1Container,
        V1ContainerPort,
        V1Deployment,
        V1DeploymentSpec,
        V1EnvFromSource,
        V1HTTPGetAction,
        V1HTTPIngressPath,
        V1HTTPIngressRuleValue,
        V1Ingress,
        V1IngressBackend,
        V1IngressRule,
        V1IngressServiceBackend,
        V1IngressSpec,
        V1IngressTLS,
        V1ObjectMeta,
        V1PersistentVolumeClaim,
        V1PersistentVolumeClaimSpec,
        V1PersistentVolumeClaimVolumeSource,
        V1PodSpec,
        V1Probe,
        V1ResourceRequirements,
        V1Secret,
        V1SecretEnvSource,
        V1Service,
        V1ServiceBackendPort,
        V1ServicePort,
        V1ServiceSpec,
        V1Volume,
        V1VolumeMount,
        V1LabelSelector,
        V1PodTemplateSpec,
        V1DeploymentStrategy,
        V1RollingUpdateDeployment,
    )
except ImportError:
    raise SystemExit("Install kubernetes: pip install kubernetes")

_api = ApiClient()


NS = "yolo-detector"
APP = "yolo-detector"
IMAGE = "yolo-detector:latest"
PORT = 8080
CAMERA_URL = "http://192.168.1.100:8081/stream"


def _labels():
    return {"app": APP}


def make_namespace():
    from kubernetes.client import V1Namespace

    return V1Namespace(
        api_version="v1",
        kind="Namespace",
        metadata=V1ObjectMeta(name=NS),
    )


def make_secret():
    return V1Secret(
        api_version="v1",
        kind="Secret",
        metadata=V1ObjectMeta(name=APP, namespace=NS),
        string_data={
            "YOLO_EMAIL_FROM": os.getenv("YOLO_EMAIL_FROM", ""),
            "YOLO_EMAIL_PASSWORD": os.getenv("YOLO_EMAIL_PASSWORD", ""),
            "YOLO_EMAIL_TO": os.getenv("YOLO_EMAIL_TO", ""),
            "YOLO_TELEGRAM_BOT_TOKEN": os.getenv("YOLO_TELEGRAM_BOT_TOKEN", ""),
            "YOLO_TELEGRAM_CHAT_ID": os.getenv("YOLO_TELEGRAM_CHAT_ID", ""),
        },
    )


def make_configmap():
    return V1ConfigMap(
        api_version="v1",
        kind="ConfigMap",
        metadata=V1ObjectMeta(name=APP, namespace=NS),
        data={
            "YOLO_HEADLESS": "true",
            "YOLO_WEB_STREAM": "true",
            "YOLO_WEB_PORT": str(PORT),
            "YOLO_FACE_DB_PATH": "/app/data/employees.pkl",
            "YOLO_CAMERA": CAMERA_URL,
        },
    )


def make_pvc():
    return V1PersistentVolumeClaim(
        api_version="v1",
        kind="PersistentVolumeClaim",
        metadata=V1ObjectMeta(name=f"{APP}-data", namespace=NS),
        spec=V1PersistentVolumeClaimSpec(
            access_modes=["ReadWriteOnce"],
            resources=V1ResourceRequirements(requests={"storage": "1Gi"}),
        ),
    )


def make_deployment():
    return V1Deployment(
        api_version="apps/v1",
        kind="Deployment",
        metadata=V1ObjectMeta(name=APP, namespace=NS, labels=_labels()),
        spec=V1DeploymentSpec(
            replicas=1,
            selector=V1LabelSelector(match_labels=_labels()),
            strategy=V1DeploymentStrategy(
                type="RollingUpdate",
                rolling_update=V1RollingUpdateDeployment(max_unavailable=0),
            ),
            template=V1PodTemplateSpec(
                metadata=V1ObjectMeta(labels=_labels()),
                spec=V1PodSpec(
                    containers=[
                        V1Container(
                            name=APP,
                            image=IMAGE,
                            image_pull_policy="IfNotPresent",
                            ports=[V1ContainerPort(container_port=PORT)],
                            env_from=[
                                V1EnvFromSource(config_map_ref=V1ConfigMapEnvSource(name=APP)),
                                V1EnvFromSource(secret_ref=V1SecretEnvSource(name=APP)),
                            ],
                            volume_mounts=[
                                V1VolumeMount(
                                    name="data", mount_path="/app/data"
                                )
                            ],
                            resources=V1ResourceRequirements(
                                requests={"cpu": "500m", "memory": "512Mi"},
                                limits={"cpu": "2", "memory": "2Gi"},
                            ),
                            startup_probe=V1Probe(
                                http_get=V1HTTPGetAction(path="/stream", port=PORT),
                                initial_delay_seconds=30,
                                period_seconds=10,
                                failure_threshold=30,
                            ),
                            liveness_probe=V1Probe(
                                http_get=V1HTTPGetAction(path="/stream", port=PORT),
                                period_seconds=30,
                                failure_threshold=3,
                            ),
                        )
                    ],
                    volumes=[
                        V1Volume(
                            name="data",
                            persistent_volume_claim=V1PersistentVolumeClaimVolumeSource(
                                claim_name=f"{APP}-data"
                            ),
                        )
                    ],
                ),
            ),
        ),
    )


def make_service():
    return V1Service(
        api_version="v1",
        kind="Service",
        metadata=V1ObjectMeta(name=APP, namespace=NS, labels=_labels()),
        spec=V1ServiceSpec(
            selector=_labels(),
            ports=[V1ServicePort(port=PORT, target_port=PORT)],
        ),
    )


def make_ingress(domain: str):
    return V1Ingress(
        api_version="networking.k8s.io/v1",
        kind="Ingress",
        metadata=V1ObjectMeta(
            name=APP,
            namespace=NS,
            labels=_labels(),
            annotations={
                "nginx.ingress.kubernetes.io/proxy-read-timeout": "600",
                "nginx.ingress.kubernetes.io/proxy-send-timeout": "600",
            },
        ),
        spec=V1IngressSpec(
            ingress_class_name="nginx",
            rules=[
                V1IngressRule(
                    host=domain,
                    http=V1HTTPIngressRuleValue(
                        paths=[
                            V1HTTPIngressPath(
                                path="/",
                                path_type="Prefix",
                                backend=V1IngressBackend(
                                    service=V1IngressServiceBackend(
                                        name=APP,
                                        port=V1ServiceBackendPort(number=PORT),
                                    ),
                                ),
                            )
                        ]
                    ),
                )
            ],
        ),
    )


def _write(path: Path, resources: list):
    path.mkdir(parents=True, exist_ok=True)
    for obj in resources:
        name = obj.kind.lower()
        dst = path / f"{name}.yaml"
        raw = yaml.dump(_api.sanitize_for_serialization(obj), default_flow_style=False, allow_unicode=True)
        with open(dst, "w", encoding="utf-8") as f:
            f.write(raw)
        print(f"  [OK] {dst}")


def main():
    global IMAGE, CAMERA_URL

    parser = argparse.ArgumentParser(description="Generate Kubernetes manifests for yolo-detector")
    parser.add_argument("--output", default="k8s", help="Output directory (default: k8s/)")
    parser.add_argument("--domain", help="Domain for Ingress (optional)")
    parser.add_argument("--image", default=IMAGE, help="Container image (default: yolo-detector:latest)")
    parser.add_argument("--camera", default=CAMERA_URL, help="Camera server URL")
    args = parser.parse_args()

    IMAGE = args.image
    CAMERA_URL = args.camera

    out = Path(args.output)
    print(f"Generating manifests -> {out}/")

    resources = [
        make_namespace(),
        make_secret(),
        make_configmap(),
        make_pvc(),
        make_deployment(),
        make_service(),
    ]
    if args.domain:
        resources.append(make_ingress(args.domain))

    _write(out, resources)
    print(f"\nDeploy:\n  kubectl apply -f {out}/")


if __name__ == "__main__":
    main()
