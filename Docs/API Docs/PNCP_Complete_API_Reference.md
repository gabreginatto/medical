# PNCP Complete API Reference - Version 2.0

Portal Nacional de Contratações Públicas (PNCP) - Complete API Documentation

## Overview

This is the **COMPLETE** PNCP API documentation extracted from the official Postman collection. Unlike the consultation-only manual, this contains all API endpoints including:
- **Item-level tender results and homologated prices** ✅
- Contract management (CRUD operations)
- Document handling
- User management
- Organizations management

**Base URL**: `{{baseUrl}}` (typically https://pncp.gov.br/api)
**Authentication**: Bearer Token required for most operations
**Data Format**: JSON

---

## 🎯 KEY ENDPOINTS FOR HOMOLOGATED PRICES

### Get Item Results (Homologated Prices)
**Endpoint**: `GET /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens/{numeroItem}/resultados`
**Purpose**: Get all results (including winning bids) for a specific item in a tender
**Authentication**: Bearer token required

**Path Parameters**:
- `cnpj`: Organization CNPJ
- `ano`: Tender year
- `sequencial`: Tender sequential number
- `numeroItem`: Item number within the tender

### Get Specific Result Details
**Endpoint**: `GET /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens/{numeroItem}/resultados/{sequencialResultado}`
**Purpose**: Get detailed information about a specific result/bid for an item
**Authentication**: Bearer token required

**Path Parameters**:
- `cnpj`: Organization CNPJ
- `ano`: Tender year
- `sequencial`: Tender sequential number
- `numeroItem`: Item number
- `sequencialResultado`: Specific result/bid sequential number

---

## 📋 COMPLETE API ENDPOINTS

### User Management (`/v1/usuarios`)

#### Authentication
- `POST /v1/usuarios/login` - Login to system

#### User CRUD Operations
- `GET /v1/usuarios` - Query users by login or CPF/CNPJ
- `GET /v1/usuarios/{id}` - Get user by ID
- `PUT /v1/usuarios/{id}` - Update user
- `DELETE /v1/usuarios/{id}` - Delete user
- `POST /v1/usuarios/{id}/orgaos` - Add authorized entities to user
- `DELETE /v1/usuarios/{id}/orgaos` - Remove authorized entities from user

### Organization Management (`/v1/orgaos`)

#### Organization Queries
- `GET /v1/orgaos/` - Query organizations by filter
- `GET /v1/orgaos/{cnpj}` - Get organization by CNPJ

### Procurement Plans (PCA) (`/v1/orgaos/{cnpj}/pca`)

#### PCA Management
- `GET /v1/orgaos/{cnpj}/pca/{ano}/{sequencial}` - Get procurement plan
- `POST /v1/orgaos/{cnpj}/pca/{ano}/{sequencial}` - Create/Update procurement plan
- `PUT /v1/orgaos/{cnpj}/pca/{ano}/{sequencial}` - Update procurement plan
- `DELETE /v1/orgaos/{cnpj}/pca/{ano}/{sequencial}` - Delete procurement plan

#### PCA Items
- `GET /v1/orgaos/{cnpj}/pca/{ano}/{sequencial}/itens` - Get all PCA items
- `POST /v1/orgaos/{cnpj}/pca/{ano}/{sequencial}/itens` - Add PCA items
- `PUT /v1/orgaos/{cnpj}/pca/{ano}/{sequencial}/itens` - Update PCA items
- `DELETE /v1/orgaos/{cnpj}/pca/{ano}/{sequencial}/itens` - Delete all PCA items
- `GET /v1/orgaos/{cnpj}/pca/{ano}/{sequencial}/itens/{numeroItem}` - Get specific PCA item
- `PUT /v1/orgaos/{cnpj}/pca/{ano}/{sequencial}/itens/{numeroItem}` - Update specific PCA item
- `DELETE /v1/orgaos/{cnpj}/pca/{ano}/{sequencial}/itens/{numeroItem}` - Delete specific PCA item
- `DELETE /v1/orgaos/{cnpj}/pca/{ano}/{sequencial}/itens/contratacao` - Delete PCA items by contracting number

### Contracting/Procurement (`/v1/orgaos/{cnpj}/compras`)

#### Contracting Management
- `GET /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}` - **Get contracting details**
- `POST /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}` - Create contracting
- `PUT /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}` - Update contracting
- `DELETE /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}` - Delete contracting

#### Contracting Documents
- `GET /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/arquivos` - Get contracting documents
- `POST /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/arquivos` - Upload contracting document
- `GET /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/arquivos/{sequencialDocumento}` - Download specific document
- `DELETE /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/arquivos/{sequencialDocumento}` - Delete document
- `GET /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/arquivos/quantidade` - Get document count

#### 🎯 Contracting Items & Results (KEY FOR HOMOLOGATED PRICES)
- `GET /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens` - **Get all tender items**
- `POST /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens` - Add tender items
- `PUT /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens` - Update tender items
- `GET /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens/{numeroItem}` - **Get specific tender item**
- `PUT /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens/{numeroItem}` - Update specific item
- `GET /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens/{numeroItem}/resultados` - **🏆 GET ITEM RESULTS/WINNING BIDS**
- `POST /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens/{numeroItem}/resultados` - Add item results
- `PUT /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens/{numeroItem}/resultados` - Update item results
- `GET /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens/{numeroItem}/resultados/{sequencialResultado}` - **🏆 GET SPECIFIC RESULT DETAILS**
- `PUT /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens/{numeroItem}/resultados/{sequencialResultado}` - Update specific result
- `GET /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens/quantidade` - Get item count

#### Item Images
- `GET /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens/{numeroItem}/imagem` - Get item images
- `POST /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens/{numeroItem}/imagem` - Upload item image
- `GET /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens/{numeroItem}/imagem/{sequencialImagem}` - Get specific image
- `DELETE /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens/{numeroItem}/imagem/{sequencialImagem}` - Delete image

#### Contracting History
- `GET /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/historico` - Get contracting history
- `GET /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/historico/quantidade` - Get history count

### Price Registration Records (`/v1/orgaos/{cnpj}/compras/{anoCompra}/{sequencialCompra}/atas`)

#### ATA Management
- `GET /v1/orgaos/{cnpj}/compras/{anoCompra}/{sequencialCompra}/atas` - Get price registration records
- `GET /v1/orgaos/{cnpj}/compras/{anoCompra}/{sequencialCompra}/atas/{sequencialAta}` - Get specific ATA
- `POST /v1/orgaos/{cnpj}/compras/{anoCompra}/{sequencialCompra}/atas/{sequencialAta}` - Create ATA
- `PUT /v1/orgaos/{cnpj}/compras/{anoCompra}/{sequencialCompra}/atas/{sequencialAta}` - Update ATA
- `DELETE /v1/orgaos/{cnpj}/compras/{anoCompra}/{sequencialCompra}/atas/{sequencialAta}` - Delete ATA

#### ATA Documents
- `GET /v1/orgaos/{cnpj}/compras/{anoCompra}/{sequencialCompra}/atas/{sequencialAta}/arquivos` - Get ATA documents
- `POST /v1/orgaos/{cnpj}/compras/{anoCompra}/{sequencialCompra}/atas/{sequencialAta}/arquivos` - Upload ATA document
- `GET /v1/orgaos/{cnpj}/compras/{anoCompra}/{sequencialCompra}/atas/{sequencialAta}/arquivos/{sequencialDocumento}` - Download ATA document
- `DELETE /v1/orgaos/{cnpj}/compras/{anoCompra}/{sequencialCompra}/atas/{sequencialAta}/arquivos/{sequencialDocumento}` - Delete ATA document
- `GET /v1/orgaos/{cnpj}/compras/{anoCompra}/{sequencialCompra}/atas/{sequencialAta}/arquivos/quantidade` - Get ATA document count

#### ATA History
- `GET /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/atas/{sequencialAta}/historico` - Get ATA history
- `GET /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/atas/{sequencialAta}/historico/quantidade` - Get ATA history count

### Contracts (`/v1/orgaos/{cnpj}/contratos`)

#### Contract Management
- `GET /v1/orgaos/{cnpj}/contratos/{ano}/{sequencial}` - Get contract
- `POST /v1/orgaos/{cnpj}/contratos/{ano}/{sequencial}` - Create contract
- `PUT /v1/orgaos/{cnpj}/contratos/{ano}/{sequencial}` - Update contract
- `DELETE /v1/orgaos/{cnpj}/contratos/{ano}/{sequencial}` - Delete contract

#### Contract Documents
- `GET /v1/orgaos/{cnpj}/contratos/{ano}/{sequencial}/arquivos` - Get contract documents
- `POST /v1/orgaos/{cnpj}/contratos/{ano}/{sequencial}/arquivos` - Upload contract document
- `GET /v1/orgaos/{cnpj}/contratos/{ano}/{sequencial}/arquivos/{sequencialDocumento}` - Download document
- `DELETE /v1/orgaos/{cnpj}/contratos/{ano}/{sequencial}/arquivos/{sequencialDocumento}` - Delete document
- `GET /v1/orgaos/{cnpj}/contratos/{ano}/{sequencial}/arquivos/quantidade` - Get document count

#### Contract Terms
- `GET /v1/orgaos/{cnpj}/contratos/{ano}/{sequencial}/termos` - Get contract terms
- `POST /v1/orgaos/{cnpj}/contratos/{ano}/{sequencial}/termos` - Add contract terms
- `GET /v1/orgaos/{cnpj}/contratos/{ano}/{sequencial}/termos/{sequencialTermo}/arquivos` - Get term documents
- `POST /v1/orgaos/{cnpj}/contratos/{ano}/{sequencial}/termos/{sequencialTermo}/arquivos` - Upload term document
- `GET /v1/orgaos/{cnpj}/contratos/{ano}/{sequencial}/termos/{sequencialTermo}/arquivos/{sequencialDocumento}` - Download term document
- `DELETE /v1/orgaos/{cnpj}/contratos/{ano}/{sequencial}/termos/{sequencialTermo}/arquivos/{sequencialDocumento}` - Delete term document
- `DELETE /v1/orgaos/{cnpj}/contratos/{ano}/{sequencial}/termos/{sequencialTermoContrato}` - Delete contract term

#### Contract History
- `GET /v1/orgaos/{cnpj}/contratos/{ano}/{sequencial}/historico` - Get contract history
- `GET /v1/orgaos/{cnpj}/contratos/{ano}/{sequencial}/historico/quantidade` - Get history count

### Credentialing (`/v1/credenciamentos`)

#### Credentialing Queries
- `GET /v1/credenciamentos` - Query credentialings
- `GET /v1/credenciamentos/{ano}/{sequencial}` - Get specific credentialing
- `GET /v1/credenciamentos/{ano}/{sequencial}/responsaveis` - Get credentialing responsibles
- `GET /v1/credenciamentos/quantidade` - Get credentialing count

---

## 🔐 Authentication

### Login
**Endpoint**: `POST /v1/usuarios/login`
**Body**:
```json
{
  "login": "your_username",
  "senha": "your_password"
}
```
**Response**: Returns Bearer token for subsequent API calls

### Using Bearer Token
Include in headers:
```
Authorization: Bearer YOUR_TOKEN_HERE
```

---

## 🎯 WORKFLOW FOR GETTING HOMOLOGATED PRICES

To get item-level homologated (winning) prices for completed tenders:

### Step 1: Find Completed Tenders
Use the consultation APIs from the previous manual to find tenders with `valorTotalHomologado > 0`

### Step 2: Get Tender Items
```bash
GET /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens
```

### Step 3: Get Item Results (Winning Bids)
For each item:
```bash
GET /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens/{numeroItem}/resultados
```

### Step 4: Get Detailed Result Information
For specific results:
```bash
GET /v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/itens/{numeroItem}/resultados/{sequencialResultado}
```

This will give you:
- Individual item homologated prices
- Winner company information
- Bid details and quantities
- Item specifications

---

## 📊 Response Structure

All endpoints return data in JSON format. Most list endpoints support pagination and return:

```json
{
  "data": [], // Array with found records
  "totalRegistros": 0, // Total records found
  "totalPaginas": 0, // Total pages needed
  "numeroPagina": 0, // Current page number
  "paginasRestantes": 0, // Remaining pages
  "empty": false // Indicates if data array is empty
}
```

---

## 🚨 Key Differences from Consultation Manual

**This complete API provides**:
✅ **Item-level tender results and homologated prices**
✅ Full CRUD operations (Create, Read, Update, Delete)
✅ Document management
✅ User and organization management
✅ Complete contracting workflow

**The consultation manual only provided**:
❌ Summary data and total values
❌ Read-only consultation endpoints
❌ No item-level detail for results

---

## 📚 Additional Resources

- **Postman Collection**: Available via the API key you provided
- **Base URL**: https://pncp.gov.br/api
- **Official Portal**: https://pncp.gov.br
- **Support**: css.serpro@serpro.gov.br

---

**Created**: 2025-01-25 from official PNCP Postman collection
**API Provider**: Serviço Federal de Processamento de Dados - Serpro