# =============================================================================
# 2. KANBAN MULTI-ETAPAS (layout ajustado)
# =============================================================================
with aba_kanban:
    st.subheader("📊 Kanban Multi-Etapas")
    with st.expander("🔍 Filtros e Ações em Lote", expanded=True):
        fk_c1, fk_c2, fk_c3, fk_c4 = st.columns([2.5, 2, 1.5, 1.5])
        with fk_c1:
            busca_kanban = st.text_input(
                "🔎 Pesquisar:",
                placeholder="Projeto, Acionamento, Nº Série, Site I, Responsável, Cliente, Site II",
                key="busca_kanban_input"
            )
        with fk_c2:
            etapas_todas = ["Projeto", "Steel", "Sankhya"]
            etapas_selecionadas = st.multiselect(
                "Etapas ativas:",
                options=etapas_todas,
                default=etapas_todas,
                key="etapas_kanban_multiselect"
            )
        with fk_c3:
            situacao_opcoes = ["Em Progresso", "Parados"]
            situacao_selecionada = st.multiselect(
                "Situação:",
                options=situacao_opcoes,
                default=situacao_opcoes,
                key="situacao_kanban_multiselect"
            )
        with fk_c4:
            st.write("")
            with st.popover("🛠️ Ações em Lote", use_container_width=True):
                st.markdown("**Aplicar nos cards selecionados:**")
                proximo_map = {"Projeto": "Steel", "Steel": "Sankhya", "Sankhya": "Concluído"}
                ids_sel = [item['id'] for _, item in df_global.iterrows()
                           if st.session_state.get(f"sel_card_{item['id']}", False)]
                if not ids_sel:
                    st.info("Nenhum card selecionado.")
                else:
                    if st.button("▶️ Iniciar Temporizador (parados)", use_container_width=True):
                        for tid in ids_sel:
                            item = df_global[df_global['id'] == tid].iloc[0]
                            if item['status_projeto'] in ['Projeto', 'Steel', 'Sankhya'] and item['estado_relogio'] == 'parado':
                                acao_iniciar_relogio(tid, item['status_projeto'].lower())
                        st.success("Ação executada!")
                        st.rerun()
                    if st.button("⏸️ Pausar Temporizador (rodando)", use_container_width=True):
                        for tid in ids_sel:
                            item = df_global[df_global['id'] == tid].iloc[0]
                            if item['status_projeto'] in ['Projeto', 'Steel', 'Sankhya'] and item['estado_relogio'] == 'rodando':
                                acao_pausar_relogio(tid, item['status_projeto'].lower())
                        st.success("Ação executada!")
                        st.rerun()
                    if st.button("✅ Avançar Etapa", use_container_width=True):
                        for tid in ids_sel:
                            item = df_global[df_global['id'] == tid].iloc[0]
                            st_proj = item['status_projeto']
                            if st_proj in proximo_map:
                                acao_finalizar_etapa(tid, st_proj, proximo_map[st_proj])
                        st.success("Ação executada!")
                        st.rerun()
                    if st.button("↩️ Retroceder Etapa", use_container_width=True):
                        for tid in ids_sel:
                            item = df_global[df_global['id'] == tid].iloc[0]
                            acao_retroceder_etapa(tid, item['status_projeto'])
                        st.success("Ação executada!")
                        st.rerun()
                    if st.button("🚫 Cancelar Projeto", use_container_width=True):
                        for tid in ids_sel:
                            item = df_global[df_global['id'] == tid].iloc[0]
                            if item['status_projeto'] in ['Projeto', 'Steel', 'Sankhya']:
                                acao_cancelar_projeto(tid, item['status_projeto'])
                        st.success("Ação executada!")
                        st.rerun()

    # Filtragem do dataframe
    df_kanban = df_global.copy()
    if busca_kanban:
        b_term = busca_kanban.lower()
        df_kanban = df_kanban[
            df_kanban['projeto'].astype(str).str.lower().str.contains(b_term) |
            df_kanban['acionamento'].astype(str).str.lower().str.contains(b_term) |
            df_kanban['num_serie'].fillna('').astype(str).str.lower().str.contains(b_term) |
            df_kanban['site_1'].fillna('').astype(str).str.lower().str.contains(b_term) |
            df_kanban['responsavel'].fillna('').astype(str).str.lower().str.contains(b_term) |
            df_kanban['cliente'].fillna('').astype(str).str.lower().str.contains(b_term) |
            df_kanban['site_2'].fillna('').astype(str).str.lower().str.contains(b_term)
        ]
    if situacao_selecionada:
        df_kanban['situacao_temp'] = df_kanban.apply(classificar_situacao, axis=1)
        df_kanban = df_kanban[df_kanban['situacao_temp'].isin(situacao_selecionada)]

    etapas_ativas = [e for e in etapas_todas if e in etapas_selecionadas]
    icones_map = {
        "Projeto": "📐 Projeto", "Steel": "⚙️ Steel", "Sankhya": "🏢 Sankhya",
        "Concluído": "✅ Concluído", "Cancelado": "🚫 Cancelado"
    }

    # Controle de exibição das colunas extras
    mostrar_concluidos = st.session_state.get("mostrar_concluidos", False)
    mostrar_cancelados = st.session_state.get("mostrar_cancelados", False)

    col_btn_conc, col_btn_canc, _ = st.columns([1, 1, 4])
    with col_btn_conc:
        if st.button("📂 Ver Finalizados" if not mostrar_concluidos else "📁 Ocultar Finalizados", use_container_width=True):
            st.session_state["mostrar_concluidos"] = not mostrar_concluidos
            st.rerun()
    with col_btn_canc:
        if st.button("📂 Ver Cancelados" if not mostrar_cancelados else "📁 Ocultar Cancelados", use_container_width=True):
            st.session_state["mostrar_cancelados"] = not mostrar_cancelados
            st.rerun()

    etapas_exibir = etapas_ativas[:]
    if mostrar_concluidos:
        etapas_exibir.append("Concluído")
    if mostrar_cancelados:
        etapas_exibir.append("Cancelado")

    if etapas_exibir:
        cols_k = st.columns(len(etapas_exibir))
        for idx, etapa_coluna in enumerate(etapas_exibir):
            with cols_k[idx]:
                st.markdown(f"#### {icones_map[etapa_coluna]}")
                df_etapa = df_kanban[df_kanban['status_projeto'] == etapa_coluna]
                if df_etapa.empty:
                    st.caption("*(Vazio)*")

                for _, item in df_etapa.iterrows():
                    id_item = item['id']
                    etapa_key = etapa_coluna.lower()

                    # Card compacto usando container com borda
                    with st.container(border=True):
                        # Linha principal do card: checkbox, info, cronômetro, botões
                        c_chk, c_info, c_tempo, c_btns = st.columns([0.2, 2.5, 1.3, 1.5])

                        with c_chk:
                            st.checkbox("", key=f"sel_card_{id_item}", label_visibility="collapsed")

                        with c_info:
                            # Nome do projeto e acionamento
                            st.markdown(
                                f"<span style='font-weight:700; font-size:14px;'>{item['projeto']}</span> "
                                f"<span style='color:#94a3b8; font-size:13px;'>{item['acionamento']}</span>",
                                unsafe_allow_html=True
                            )
                            # Cliente e Site I
                            st.markdown(
                                f"<span style='font-size:13px; color:#cbd5e1;'>"
                                f"{item['cliente']} | Site I: {item['site_1'] or '-'}</span>",
                                unsafe_allow_html=True
                            )

                        with c_tempo:
                            segundos = obter_tempo_decorrido_etapa(item, etapa_key)
                            tempo_str = formatar_segundos(segundos)
                            status_ico = "🟢" if item['estado_relogio'] == 'rodando' else "🔴"
                            st.markdown(
                                f"<span style='font-size:13px;'>⏱️ <code>{tempo_str}</code> {status_ico}</span>",
                                unsafe_allow_html=True
                            )

                        with c_btns:
                            # Botões de ação compactos
                            if etapa_coluna in ["Projeto", "Steel", "Sankhya"]:
                                btn_cols = st.columns(5)
                                with btn_cols[0]:
                                    if item['estado_relogio'] == 'parado':
                                        if st.button("▶️", key=f"k_start_{id_item}", help="Iniciar", use_container_width=True):
                                            acao_iniciar_relogio(id_item, etapa_key)
                                            st.rerun()
                                    else:
                                        if st.button("⏸️", key=f"k_pause_{id_item}", help="Pausar", use_container_width=True):
                                            acao_pausar_relogio(id_item, etapa_key)
                                            st.rerun()
                                with btn_cols[1]:
                                    if etapa_coluna in ["Projeto", "Steel", "Sankhya"]:
                                        proxima_etapa = {"Projeto": "Steel", "Steel": "Sankhya", "Sankhya": "Concluído"}[etapa_coluna]
                                        if st.button("✅", key=f"k_fin_{id_item}", help="Avançar", use_container_width=True):
                                            acao_finalizar_etapa(id_item, etapa_coluna, proxima_etapa)
                                            st.rerun()
                                with btn_cols[2]:
                                    if etapa_coluna != "Projeto":
                                        if st.button("↩️", key=f"k_back_{id_item}", help="Retroceder", use_container_width=True):
                                            acao_retroceder_etapa(id_item, etapa_coluna)
                                            st.rerun()
                                with btn_cols[3]:
                                    with st.popover("ℹ️", key=f"k_info_{id_item}", help="Detalhes"):
                                        # Aplicando CSS para limitar tamanho do popover
                                        st.markdown("""
                                            <style>
                                            div[data-testid="stPopover"] {
                                                max-width: 450px !important;
                                                max-height: 80vh !important;
                                                overflow-y: auto !important;
                                            }
                                            </style>
                                        """, unsafe_allow_html=True)
                                        st.markdown(f"**Projeto:** {item['projeto']}")
                                        st.markdown(f"**Acionamento:** {item['acionamento']}")
                                        st.markdown(f"**Cliente:** {item['cliente']}")
                                        st.markdown(f"**Site I:** {item['site_1'] or '-'}")
                                        st.markdown(f"**Site II:** {item['site_2'] or '-'}")
                                        st.markdown(f"**Nº Série:** {item['num_serie'] or '-'}")
                                        st.markdown(f"**Local:** {item['local'] or '-'}")
                                        st.markdown(f"**Elemento:** {item['elemento'] or '-'}")
                                        st.markdown(f"**Tipo:** {item['tipo']}")
                                        st.markdown(f"**Finalidade:** {item['finalidade']}")
                                        st.markdown(f"**Peso:** {item['peso']} kg")
                                        st.markdown(f"**Responsável:** {item['responsavel']}")
                                        st.markdown(f"**Data:** {item['data']}")
                                        st.markdown(f"**Prazo:** {item['prazo']}")
                                        st.markdown(f"**Observações:** {item['observacoes'] or '-'}")
                                        st.divider()
                                        col_pop1, col_pop2 = st.columns(2)
                                        with col_pop1:
                                            if st.button("✏️ Editar", key=f"k_edit_pop_{id_item}", use_container_width=True):
                                                st.session_state[f"editing_{id_item}"] = True
                                                st.rerun()
                                        with col_pop2:
                                            if st.button("🚫 Cancelar", key=f"k_canc_pop_{id_item}", use_container_width=True):
                                                acao_cancelar_projeto(id_item, etapa_coluna)
                                                st.rerun()

                            elif etapa_coluna == "Concluído":
                                if st.button("↩️ Retornar", key=f"k_back_conc_{id_item}", use_container_width=True):
                                    acao_retroceder_etapa(id_item, etapa_coluna)
                                    st.rerun()
                            elif etapa_coluna == "Cancelado":
                                if st.button("↩️ Reativar", key=f"k_back_canc_{id_item}", use_container_width=True):
                                    acao_retroceder_etapa(id_item, etapa_coluna)
                                    st.rerun()

    # Formulário de edição (exibido abaixo do Kanban se algum item estiver em edição)
    for id_item in df_global['id']:
        if st.session_state.get(f"editing_{id_item}", False):
            with st.expander(f"✏️ Editando projeto #{id_item}", expanded=True):
                item = df_global[df_global['id'] == id_item].iloc[0]
                loc_k = obter_locais_cadastrados()
                elem_k = obter_elementos_cadastrados()
                cli_k = obter_clientes()
                resp_k = obter_responsaveis()
                with st.form(key=f"k_edit_form_{id_item}"):
                    col_form1, col_form2, col_form3 = st.columns(3)
                    with col_form1:
                        e_ac = st.text_input("Acionamento", value=item['acionamento'])
                        e_proj = st.text_input("Projeto", value=item['projeto'])
                        e_rev = st.text_input("Revisão", value=item['revisao'] or '00')
                        e_cli = st.selectbox("Cliente", options=cli_k, index=cli_k.index(item['cliente']) if item['cliente'] in cli_k else 0)
                        e_tipo = st.selectbox("Tipo", ["Torre", "Rooftop", "Item para site", "Projeto interno"])
                    with col_form2:
                        e_fin = st.selectbox("Finalidade", ["Fabricação", "Estimativa de Custo"])
                        e_peso = st.number_input("Peso (kg)", value=float(item['peso']))
                        e_s1 = st.text_input("Site I", value=item['site_1'] or '')
                        e_s2 = st.text_input("Site II", value=item['site_2'] or '')
                        e_ns = st.text_input("Nº Série", value=item['num_serie'] or '')
                    with col_form3:
                        e_l_atual = str(item['local'] or '')
                        idx_lk = loc_k.index(e_l_atual) + 1 if e_l_atual in loc_k else 0
                        e_lk_ex = st.selectbox("Local / Cidade (Padrão)", options=[""] + loc_k, index=idx_lk, key=f"k_lk_ex_{id_item}")
                        e_lk_nv = st.text_input("Ou digite um novo Local", value="" if idx_lk > 0 else e_l_atual, key=f"k_lk_nv_{id_item}")
                        e_el_atual = str(item['elemento'] or '')
                        idx_ek = elem_k.index(e_el_atual) + 1 if e_el_atual in elem_k else 0
                        e_ek_ex = st.selectbox("Elemento (Padrão)", options=[""] + elem_k, index=idx_ek, key=f"k_ek_ex_{id_item}")
                        e_ek_nv = st.text_input("Ou digite um novo Elemento", value="" if idx_ek > 0 else e_el_atual, key=f"k_ek_nv_{id_item}")
                        e_resp = st.selectbox("Responsável", options=resp_k, index=resp_k.index(item['responsavel']) if item['responsavel'] in resp_k else 0)
                    try:
                        dt_p = datetime.strptime(str(item['data']), "%d/%m/%Y").date()
                    except:
                        dt_p = agora_br().date()
                    e_data_k = st.date_input("Data de Cadastro", value=dt_p, key=f"k_data_{id_item}")
                    e_prazo = st.text_input("Prazo", value=item['prazo'])
                    e_obs = st.text_area("Observações", value=item['observacoes'] or "")
                    col_save, col_cancel_edit = st.columns(2)
                    with col_save:
                        if st.form_submit_button("Salvar"):
                            e_l_final = e_lk_nv.strip() if e_lk_nv.strip() else e_lk_ex
                            e_el_final = e_ek_nv.strip() if e_ek_nv.strip() else e_ek_ex
                            editar_torre_completo(id_item, e_ac, e_proj, e_rev, e_tipo, e_fin, e_peso, e_s1, e_s2, e_ns,
                                                  e_l_final, e_el_final, e_cli, e_resp, e_data_k.strftime("%d/%m/%Y"), e_prazo, e_obs)
                            st.session_state[f"editing_{id_item}"] = False
                            st.rerun()
                    with col_cancel_edit:
                        if st.form_submit_button("Cancelar"):
                            st.session_state[f"editing_{id_item}"] = False
                            st.rerun()
