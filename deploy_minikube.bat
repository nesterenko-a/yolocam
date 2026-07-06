@echo off
REM Deploy yolo-detector to minikube

echo Generating manifests...
python generate_k8s.py
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
