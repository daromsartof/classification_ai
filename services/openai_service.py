from openai import OpenAI
import os
import json
from repositories.ai_separation_context_repository import AiSeparationContextRepository
from services import constant
from services.utils_service import UtilsService
from services.logger import Logger

logger = Logger.get_logger()
class OpenAIService:
    def __init__(self, model="gpt-4o-mini"):
        self.client = OpenAI(
            api_key= os.getenv("OPENAI_API_KEY")
        )
        self.model = model

    def response_parse(self, response):
        try:
            parsed_response = json.loads(response)
        except json.JSONDecodeError:
            # Try cleaning the response by removing ```json and ```
            cleaned_response = response.replace('```json\n', '').replace('```', '').strip()
            try:
                parsed_response = json.loads(cleaned_response)
            except json.JSONDecodeError as err:
                raise ValueError('Failed to parse response after cleaning') from err
        return parsed_response

    def callAgent(self, systemPrompt: str,  userPrompt: str, model: str = "gpt-4o-mini") -> str:
        logger.info(f"model : {model}")
        completion = self.client.chat.completions.create(
            model=model or self.model,
            messages=[
                {"role": "system", "content": systemPrompt},
                {"role": "user", "content": userPrompt}
            ]   
        )
        return completion.choices[0].message.content
    
    def categorisation(self, userPrompt: str, image: dict, model: str, prompt_system: str) -> str:
        try:
            ai_separation_context_repository = AiSeparationContextRepository()
            utils_service = UtilsService()
            fournisseurs, clients = utils_service.getFournisseurAndClientsList(image.get('dossier_id', None))

            # Replace placeholders with proper error handling
            replacements = {
                '{{dossier_nom}}': image.get('rs_ste', ''),
                '{{dossier_siren}}': image.get('siren_ste', ''),
                '{{dossier_rs}}': image.get('rs_ste', ''),
                '{{dossier_ape}}': image.get('ape', ''),
                '{{autre_remarque}}': "",
                '{{list_des_erreurs_fournisseurs}}': "",
                '{{list_des_erreurs_client}}': "",
                '{{custom_critaire_banque}}': "",
                '{{custom_critaire_gestion}}': "",
                '{{document_text}}': userPrompt,
                '{{activite_com_cat}}': image.get('activite_0', ''),
                '{{activite_com_cat_1}}': image.get('activite_1', ''),
                '{{activite_com_cat_2}}': image.get('activite_2', ''),
                '{{activite_com_cat_3}}': image.get('activite_3', ''), 
                '{{dossier_tiers_list}}': clients,
                '{{dossier_tiers_list_fournisseur}}': fournisseurs,
                '{{custom_critaire_courrier}}': "",
                '{{custom_critaire_fiscal}}': "",
                '{{custom_critaire_social}}': "",
                '{{custom_critaire_caisse}}': "",
                '{{custom_critaire_frais}}': "",
            }
            custom_context = ai_separation_context_repository.get_ai_separation_context_by(
                dossier=image.get('dossier_id', None), 
                site=image.get('site_id', None), 
                client=image.get('client_id', None)
            )
            for context in custom_context:
                if context.get('categorie_id', None) == constant.categirie_id.get('fournisseur', None):
                    replacements['{{list_des_erreurs_fournisseurs}}'] += f"{context.get('contexte', '')}, "
                elif context.get('categorie_id', None) == constant.categirie_id.get('client', None):
                    replacements['{{list_des_erreurs_client}}'] += f"{context.get('contexte', '')}, "
                elif context.get('categorie_id', None) == constant.categirie_id.get('banque', None):
                    replacements['{{custom_critaire_banque}}'] += f"{context.get('contexte', '')}, "
                elif context.get('categorie_id', None) == constant.categirie_id.get('gestion', None):
                    replacements['{{custom_critaire_gestion}}'] += f"{context.get('contexte', '')}, "
                elif context.get('categorie_id', None) == constant.categirie_id.get('courrier', None):
                    replacements['{{custom_critaire_courrier}}'] += f"{context.get('contexte', '')}, "
                else:
                    replacements['{{autre_remarque}}'] += f"{context.get('contexte', '')}, "
                
            # Safely get dossier_id and handle potential missing keys
            dossier_id = str(image.get('dossier_id', ''))
            
            for placeholder, value in replacements.items():
                if(prompt_system):
                    prompt_system = prompt_system.replace(placeholder, value)

            # Call the agent with proper parameter names
            response = self.callAgent(
                systemPrompt=prompt_system,
                userPrompt=f"voici le contenu de la première page du document : {userPrompt}",
                model=model
            )
            logger.info(f"Raw response from OpenAI: {response}")  # Debugging line to see the raw response
            return self.response_parse(response)
            
        except Exception as e:
            # Log the actual error for debugging
            logger.error(f"Categorization error: {str(e)}")
            return {
                "Categorie": "ILLISIBLES",
                "ID": 18,
                "Explication": f"Erreur GPT: {str(e)}"
            }
            
    def validation(self, userPrompt: str, image: dict, model: str = "gpt-4o-mini") -> str:
        try:
            utils_service = UtilsService()
            fournisseurs, clients = utils_service.getFournisseurAndClientsList(image.get('dossier_id', None))
            system_prompt = ""
            prompt_path = 'services/prompts/validation.md'  
            with open(prompt_path, 'r', encoding='utf-8') as f:
                system_prompt = f.read()

            system_prompt = system_prompt.replace('{{dossier_nom}}', image.get('dossier_nom', ''))
            system_prompt = system_prompt.replace('{{dossier_ape}}', image.get('ape', ''))
            system_prompt = system_prompt.replace('{{activite_com_cat}}', image.get('activite_0', ''))
            system_prompt = system_prompt.replace('{{activite_com_cat_1}}', image.get('activite_1', ''))
            system_prompt = system_prompt.replace('{{activite_com_cat_2}}', image.get('activite_2', ''))
            system_prompt = system_prompt.replace('{{activite_com_cat_3}}', image.get('activite_3', ''))
            system_prompt = system_prompt.replace('{{document_text}}', userPrompt)
            system_prompt = system_prompt.replace('{{dossier_tiers_list}}', clients)
            system_prompt = system_prompt.replace('{{dossier_tiers_list_fournisseur}}', fournisseurs)
            system_prompt = system_prompt.replace('{{recepteur}}', image.get('Recepeutteur', ''))
            response = self.callAgent(
                systemPrompt=system_prompt,
                userPrompt=f"voici le contenu de la première page du document : {userPrompt}",
                model=model
            )
            
            return self.response_parse(response)

            
        except Exception as e:
            # Log the actual error for debugging
            logger.error(f"Validation error: {str(e)}")
            return {
                "Categorie": "ILLISIBLES",
                "ID": 18,
                "Explication": f"Erreur GPT: {str(e)}"
            }