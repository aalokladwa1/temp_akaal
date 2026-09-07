{{/*
P7B.20 -- shared name helpers. No secret material, no plan/migration references here --
naming only.
*/}}

{{- define "akaal-worker-fabric.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "akaal-worker-fabric.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name (include "akaal-worker-fabric.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "akaal-worker-fabric.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "akaal-worker-fabric.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- required "serviceAccount.name is required when serviceAccount.create is false -- there is no default service account for this workload" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{- define "akaal-worker-fabric.labels" -}}
app.kubernetes.io/name: {{ include "akaal-worker-fabric.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
akaal.io/component: worker-fabric
{{- end -}}

{{- define "akaal-worker-fabric.image" -}}
{{- if .Values.image.digest -}}
{{- printf "%s@%s" .Values.image.repository .Values.image.digest -}}
{{- else -}}
{{- required "image.tag is required (no default 'latest' is provided by this chart)" .Values.image.tag | printf "%s:%s" .Values.image.repository -}}
{{- end -}}
{{- end -}}
