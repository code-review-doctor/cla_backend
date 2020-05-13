{{/* vim: set filetype=mustache: */}}
{{/*
Expand the name of the chart.
*/}}
{{- define "cla-backend.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "cla-backend.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "cla-backend.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Common labels
*/}}
{{- define "cla-backend.labels" -}}
helm.sh/chart: {{ include "cla-backend.chart" . }}
{{ include "cla-backend.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{/*
Selector labels
*/}}
{{- define "cla-backend.selectorLabels" -}}
app.kubernetes.io/name: {{ include "cla-backend.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/*
Create the name of the service account to use
*/}}
{{- define "cla-backend.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
    {{ default (include "cla-backend.fullname" .) .Values.serviceAccount.name }}
{{- else -}}
    {{ default "default" .Values.serviceAccount.name }}
{{- end -}}
{{- end -}}

{{/*
Local postgres env vars
*/}}
{{- define "cla-backend.localPostgresEnvVars" -}}
{{- if .Values.localPostgres.enabled }}
- name: DB_HOST
  value: {{ include "cla-backend.fullname" . }}-db
- name: DB_PORT
  value: "5432"
{{- end }}
{{- end -}}

{{- define "cla-backend.app.vars" -}}
- name: DB_HOST
  value: {{ include "cla-backend.fullname" . }}-db
- name: DB_PORT
  value: "5432"
- name: DB_PASSWORD
  valueFrom:
    secretKeyRef:
      name: db
      key: password
      optional: true
- name: DB_PASSWORD
  valueFrom:
    secretKeyRef:
      name: db
      key: name
      optional: true
- name: ALLOWED_HOSTS
  value: "{{ .Values.host }}"
- name: LOG_LEVEL
  value: "{{ .Values.logLevl }}"
- name: AWS_ACCESS_KEY_ID
  valueFrom:
    secretKeyRef:
      name: s3
      key: access_key_id
      optional: true
- name: AWS_SECRET_ACCESS_KEY
  valueFrom:
    secretKeyRef:
      name: s3
      key: secret_access_key
      optional: true
- name: AWS_STORAGE_BUCKET_NAME
  valueFrom:
    secretKeyRef:
      name: s3
      key: bucket_name
      optional: true
- name: OBIEE_ZIP_PASSWORD
  valueFrom:
    secretKeyRef:
      name: obiee-zip
      key: password
      optional: true
{{ if .Values.worker.enabled }}
- name: CELERY_BROKER_URL
  {{ if .Values.worker.url }}
  value: {{ .Values.worker.url }}
  {{ else }}
  valueFrom:
    secretKeyRef:
      name: ec-cluster
      key: url
  {{ end }}
{{ end }}
  {{ range .Values.envVars }}
- name: {{ .name }}
  value: "{{ .value }}"
  {{ end }}
{{- end -}}