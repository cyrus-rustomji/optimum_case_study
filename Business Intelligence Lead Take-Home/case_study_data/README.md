# OP Mainnet Case Study Data

Daily datasets about OP Mainnet activity, fees, and apps.

- **Window:** 2025-01-01 through 2026-09-15 (inclusive, UTC days).
- **Sources:** Allium (Snowflake) for all files except 08 and 11, which come from DefiLlama.
  File 07 combines Allium and Dune labels.
- **Format:** one CSV per dataset in `csv/`. The same rows are in `data/` as JSON.
- **Method:** the SQL for every file is in `queries/`, with the same file name.
- **Pulled:** 2026-09-23. Sources revise recent days, so a re-run can differ slightly.

All USD values use the source's own prices. ETH amounts are in ETH, not wei.

## Core datasets

### 01_opm_fees_daily
Transaction fees paid by users on OP Mainnet, one row per day.

| Column | Meaning |
|---|---|
| `fee_paying_txs` | Transactions that paid a fee (system deposit txs excluded) |
| `execution_fee_eth` | L2 execution fee: gas used × gas price |
| `l1_data_fee_eth` | L1 data fee: the part of the fee charged for posting the tx data to Ethereum |
| `total_fee_eth` | Execution fee + L1 data fee |
| `eth_price_usd` | Daily median ETH price (same as file 02) |
| `*_usd` | ETH amounts × `eth_price_usd` |

This file shows fees paid by users on OP Mainnet. It does not include any costs paid on Ethereum.

### 02_eth_price_daily
Daily median ETH/USD price.

### 03_opm_activity_daily
| Column | Meaning |
|---|---|
| `total_transactions` | All transactions, including failed ones and one system tx per block |
| `success_transactions` / `failed_transactions` | Split of the total by outcome |
| `active_addresses` | Distinct addresses that sent at least one successful tx that day |
| `active_contracts` | Distinct contracts that were called that day |

### 04_opm_new_addresses_daily
| Column | Meaning |
|---|---|
| `new_addresses` | Addresses that sent their first-ever transaction that day |
| `returning_addresses` | Active addresses that had sent a transaction before |

### 05_opm_contract_deployments_daily
| Column | Meaning |
|---|---|
| `new_deployed_contracts` | Contracts created that day, including contracts created by other contracts |
| `distinct_contract_deployers` | Distinct addresses that created at least one contract |

### 06_opm_contract_activity_daily
Transactions and fees by destination address (the tx `to_address`), one row per day per address.

**Address rule.** An address has its own rows if, in at least one calendar month, it received
at least 10,000 transactions **or** at least 0.25 ETH of fees. 1,082 addresses meet the rule. All
other addresses are summed into one daily row where `to_address = 'other'`. That row also holds
contract-creation transactions, which have no `to_address`. The rows for each day add up to the
daily totals in file 01.

| Column | Meaning |
|---|---|
| `txs` / `successful_txs` | Transactions sent to the address |
| `distinct_senders` | Distinct addresses that sent those transactions |
| `gas_used` | Total L2 gas used by those transactions |
| `execution_fee_eth`, `l1_data_fee_eth`, `total_fee_eth` | Same definitions as file 01 |
| `total_fee_usd` | `total_fee_eth` × the daily ETH price |

The sender pays the fee. This file assigns each fee to the address the transaction was sent to.
That address can be the app itself, a router, an aggregator, or a bot contract.

### 07_opm_contract_labels
One row for each of the 1,082 addresses in file 06. Labels come from two sources: Allium (no
prefix) and Dune (`dune_` prefix). A blank cell means that source has no record. Where a source has
more than one label for an address, the labels are separated by `|`.

| Column | Meaning |
|---|---|
| `address_type` | `contract` if Allium has a deployment record for it or it emitted an event log in the window; otherwise `wallet` |
| `deployed_date` | Deployment date, where Allium has a record |
| `display_name` | Allium's display name for the address |
| `entity_project`, `entity_category`, `entity_name` | Owner from Allium's entity registry (for example `uniswap`, `dex`) |
| `tags` | All Allium explorer tags on the address |
| `dune_label_name`, `dune_label_category` | Dune's name for what the address is (for example `Seaport: Seaport`, `contracts`) |
| `dune_namespace`, `dune_contract_name` | Project and contract name from Dune's decoded contract registry |
| `dune_owner` | Entity that controls the address, from Dune's ownership registry |
| `dune_token_symbol` | Token symbol, if the address is a token contract |
| `dune_cex_name` | Exchange name, if the address is an exchange-owned wallet |
| `dune_persona` | Dune's behavior labels: what the address has done (for example `DEX Trader`, `Odos User`). These describe activity, not identity |

About 340 of the 1,082 addresses have a name from at least one source. The rest have no name.

### 08_opm_app_fees_revenue_daily (DefiLlama)
Fees that users paid to apps on OP Mainnet, by protocol and day.

| Column | Meaning |
|---|---|
| `protocol` / `sub_protocol` | Parent brand / specific version (for example `aave` / `aave-v3`) |
| `category` | DefiLlama category |
| `fee_usd` | Total fees users paid to the app |
| `revenue_usd` | The part of `fee_usd` the app keeps |
| `holder_revenue_usd` | The part paid to the app's token holders |

These are app fees. They are separate from the transaction fees in file 01.

## Additional datasets

### 09_opm_dex_volume_daily
DEX trading by project and protocol (`protocol` = the AMM codebase and version).
`total_volume_usd`, `total_swap_count`, `total_transactions`, and `active_users` (distinct traders
that day). Do not sum `active_users` across days.

### 10_opm_lending_daily
Lending by project and protocol.

- Daily flows, safe to sum across days: `deposit_volume_usd`, `withdrawal_volume_usd`,
  `loan_volume_usd`, `repayment_volume_usd`, `liquidation_volume_usd`.
- End-of-day balances, not safe to sum across days: `tvl_usd`, `outstanding_loans_usd`,
  `supplied_amount_usd`.
- `tvl_usd` here excludes assets lent out to borrowers, so it differs from file 11.

### 11_opm_tvl_by_protocol_daily (DefiLlama)
TVL (total value locked: the USD value of assets deposited in each app), by protocol and day.
Standard deposits only; borrowed, staking, and treasury amounts are excluded.

To match DefiLlama's headline OP Mainnet TVL, keep rows where `exclude_from_global_tvl = false`
**and** `has_double_counted_tvl = false`. Summing every row counts some assets more than once.

### 12_opm_stablecoins_daily
One row per day per stablecoin token contract.

| Column | Meaning |
|---|---|
| `is_native` | `true` for issuer-deployed tokens (for example native USDC), `false` for bridged copies (for example USDC.e) |
| `total_supply_usd` / `circulating_supply_usd` | End-of-day supply; circulating excludes issuer treasury balances |
| `transfer_tx_count`, `transfer_count` | Transactions with a transfer of this token / transfer events |
| `transfer_volume_usd` | USD value of every transfer, including bot and contract transfers that move the same dollars many times a day |
| `adjusted_volume_usd` | Allium's filtered volume: bot and internal contract transfers removed |
| `sender_count`, `recipient_count` | Distinct senders / recipients that day |

Supply can be summed across tokens on one day. Do not sum it across days.

### 13_opm_bridge_flows_daily
Bridge activity into and out of OP Mainnet, by day, bridge type, bridge, direction, and counterparty chain.

| Column | Meaning |
|---|---|
| `bridge_type` | `canonical` = OP Mainnet's own Standard Bridge to Ethereum; `bridge` = app bridges (Across, Stargate, ...); `messaging_protocol` = messaging layers (Circle CCTP, LayerZero, ...); `bridge_aggregator` = routers on top of other bridges (LiFi, Bungee, ...) |
| `direction` | `inbound` = into OP Mainnet; `outbound` = out of OP Mainnet |
| `counterparty_chain` | The other chain. The 25 largest chains by USD volume are named; the rest are `other`. `unknown` = the source did not record it |
| `events` | Bridge events |
| `token_events` | Events that carried a priced token amount |
| `users` | Distinct senders (outbound) or recipients (inbound) that day |
| `usd_volume` | USD value of the tokens moved |

- An aggregator transfer can also show up as a row of the bridge it routes through.
  Do not add `bridge_aggregator` volume to the other types.
- Single transfers priced above $1B are treated as unpriced. Those prices come from bad price ticks.
- The source uses two names for one chain in a few cases (for example `lyra` and `lyra_chain`).

### 14_opm_cex_flows_daily
Centralized exchange (CEX) deposits and withdrawals on OP Mainnet, by exchange, token, and day.

| Column | Meaning |
|---|---|
| `amount_in` / `usd_amount_in` | Tokens deposited to the exchange's addresses, including user deposit addresses |
| `amount_out` / `usd_amount_out` | Tokens withdrawn from the exchange |
| `net_usd_amount` | `usd_amount_in − usd_amount_out` (positive = net flow into the exchange) |

Allium publishes this data pre-aggregated, so it has volumes but no transfer counts. It covers
only addresses Allium links to an exchange, so totals are a lower bound.

## Known quirks

- File 07 marks the zero address (`0x000...000`) as a contract with a 2024 deployment date. This is
  an artifact in the source data.
- Allium and DefiLlama each have their own "TVL" figure, and the two differ. Files 10 and 11 use
  different definitions on purpose; see the notes above.
