# Docker Env Example Specification

## Purpose

Docker build MUST copy the tracked env example whose filename is `env.example`.

## Requirements

### Requirement: Copy real env example filename

The Docker image build MUST copy `env.example` into the image as `.env`. Header copy instructions in `env.example` MUST name `env.example`.

#### Scenario: Build copies env.example

- GIVEN a Docker image build of the project
- WHEN the build copies an environment template
- THEN the source filename MUST be `env.example`
- AND the destination MUST be `.env`

#### Scenario: Template header names the file

- GIVEN a reader following `env.example` setup
- WHEN they copy the template locally
- THEN the documented source path MUST be `env.example`
