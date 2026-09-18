//! BRICS Pay REST API Server
//! 
//! Provides HTTP endpoints for interacting with the BRICS Pay network

use actix_web::{web, App, HttpServer, HttpResponse, get, post};
use serde::{Deserialize, Serialize};

#[derive(Serialize)]
struct ApiResponse<T> {
    success: bool,
    data: Option<T>,
    error: Option<String>,
}

#[derive(Deserialize)]
struct TransactionRequest {
    from: String,
    to: String,
    amount: u64,
    currency: String,
}

#[derive(Serialize)]
struct TransactionResponse {
    transaction_id: String,
    status: String,
    timestamp: u64,
}

#[derive(Serialize)]
struct BalanceResponse {
    account_id: String,
    balances: Vec<CurrencyBalance>,
}

#[derive(Serialize)]
struct CurrencyBalance {
    currency: String,
    amount: u64,
}

#[get("/health")]
async fn health_check() -> HttpResponse {
    let response = ApiResponse::<()> {
        success: true,
        data: None,
        error: None,
    };
    HttpResponse::Ok().json(response)
}

#[get("/api/v1/accounts/{account_id}/balance")]
async fn get_balance(path: web::Path<String>) -> HttpResponse {
    let account_id = path.into_inner();
    
    let response = ApiResponse {
        success: true,
        data: Some(BalanceResponse {
            account_id,
            balances: vec![
                CurrencyBalance {
                    currency: "BRL".to_string(),
                    amount: 0,
                },
                CurrencyBalance {
                    currency: "INR".to_string(),
                    amount: 0,
                },
            ],
        }),
        error: None,
    };
    
    HttpResponse::Ok().json(response)
}

#[post("/api/v1/transactions")]
async fn create_transaction(body: web::Json<TransactionRequest>) -> HttpResponse {
    let _tx_req = body.into_inner();
    
    let response = ApiResponse {
        success: true,
        data: Some(TransactionResponse {
            transaction_id: "tx_".to_string() + &uuid::Uuid::new_v4().to_string(),
            status: "pending".to_string(),
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs(),
        }),
        error: None,
    };
    
    HttpResponse::Created().json(response)
}

#[get("/api/v1/transactions/{tx_id}")]
async fn get_transaction(path: web::Path<String>) -> HttpResponse {
    let _tx_id = path.into_inner();
    
    let response = ApiResponse::<TransactionResponse> {
        success: false,
        data: None,
        error: Some("Transaction not found".to_string()),
    };
    
    HttpResponse::NotFound().json(response)
}

#[actix_web::main]
async fn main() -> std::io::Result<()> {
    println!("BRICS Pay REST API Server starting...");
    println!("Listening on http://0.0.0.0:8080");
    
    HttpServer::new(|| {
        App::new()
            .service(health_check)
            .service(get_balance)
            .service(create_transaction)
            .service(get_transaction)
    })
    .bind("0.0.0.0:8080")?
    .run()
    .await
}
