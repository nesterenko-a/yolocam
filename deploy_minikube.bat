@echo off
REM Deploy yolo-detector to minikube
REM Usage: deploy_minikube.bat [camera_url]
REM        deploy_minikube.bat http://host.minikube.internal:8081/stream

set CAMERA=%1
if "%CAMERA%"=="" set CAMERA=http://host.minikube.internal:8081/stream

echo Generating manifests with CAMERA=%CAMERA%...
python generate_k8s.py --camera "%CAMERA%"
IF %ERRORLEVEL% NEQ 0 EXIT /B %ERRORLEVEL%

echo Building image...
docker build -t yolo-detector:latest -f docker/Dockerfile .
IF %ERRORLEVEL% NEQ 0 EXIT /B %ERRORLEVEL%

echo Loading into minikube...
minikube image load yolo-detector:latest
IF %ERRORLEVEL% NEQ 0 EXIT /B %ERRORLEVEL%

echo Applying manifests...
kubectl apply -f k8s\
IF %ERRORLEVEL% NEQ 0 EXIT /B %ERRORLEVEL%

echo.
echo Open in browser:
minikube service yolo-detector -n yolo-detector --url
echo.
echo Or stream at http://localhost:8080  (kubectl port-forward)
