# Rust service profile

Use a clear `src/` or workspace layout with `main`, bootstrap/config/error,
domain, application, transport, and infrastructure boundaries. Use Tokio/Axum
where HTTP is needed, SQLx for PostgreSQL access, and Liquibase for schema
evolution. No frontend is required; apply Rust, resource, security, testing,
observability, API, and database rules that are relevant.

## Primary sources

[Rust](https://doc.rust-lang.org/), [Tokio](https://tokio.rs/), and
[Axum](https://docs.rs/axum/).
