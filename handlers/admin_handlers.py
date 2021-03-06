from base import *
import json

#--------------------------------------------------------LOGIN PAGE------------------------------------------------------------
class LoginHandler(BaseHandler): 
    @tornado.web.addslash
    def get(self):
        with open("templates/us/settings.json") as json_file:
            settings = json.load(json_file)
        self.render(
            "admin/login.html", 
            next=self.get_argument("next","/"), 
            message=self.get_argument("error",""),
            page_title="Please Login",
            page_heading="Login to OD500" ,
            lan='en',
            country='us',
            menu=settings['menu']['en'],
            settings=settings
            )

    def post(self):
        username = self.get_argument("username", "")
        password = self.get_argument("password", "").encode('utf-8')
        try: 
            user = models.Users.objects.get(username=username)
        except Exception, e:
            logging.info('unsuccessful login')
            error_msg = u"?error=" + tornado.escape.url_escape("User does not exist")
            self.redirect(u"/login" + error_msg)
        if user and user.password and bcrypt.hashpw(password, user.password.encode('utf-8')) == user.password:
            logging.info('successful login for '+username)
            self.set_current_user(username)
            self.redirect("/admin/companies/")
        else: 
            logging.info('unsuccessful login')
            error_msg = u"?error=" + tornado.escape.url_escape("Incorrect Password")
            self.redirect(u"/login" + error_msg)

    def set_current_user(self, user):
        logging.info('setting ' + user)
        if user:
            self.set_secure_cookie("user", tornado.escape.json_encode(user))
        else: 
            self.clear_cookie("user")

#--------------------------------------------------------REGISTER PAGE------------------------------------------------------------
class RegisterHandler(LoginHandler):
    @tornado.web.addslash
    @tornado.web.authenticated
    def get(self):
        try:
            user = models.Users.objects.get(username=self.current_user)
        except Exception, e:
            logging.info("Could not get user: " + str(e))
            self.redirect("/login/")
        country = user.country
        with open("templates/" + country + "/settings.json") as json_file:
            settings = json.load(json_file)
        lan = settings['default_language']
        self.render(
                "admin/register.html", 
                next=self.get_argument("next","/"),
                page_title="Register",
                page_heading="Register for OD500",
                user=self.current_user,
                country = country,
                country_keys=country_keys,
                menu=settings['menu'][lan],
                settings=settings,
                lan=lan
            )

    @tornado.web.authenticated
    def post(self):
        username = self.get_argument("username", "")
        try:
            user = models.Users.objects.get(username=username)
        except:
            user = ''
        if user:
            error_msg = u"?error=" + tornado.escape.url_escape("Login name already taken")
            self.redirect(u"/register" + error_msg)
        else: 
            password = self.get_argument("password", "")
            hashedPassword = bcrypt.hashpw(password, bcrypt.gensalt(8))
            country = self.get_argument("country", None)
            newUser = models.Users(
                username=username,
                password = hashedPassword,
                country=country
                )
            newUser.save()
            self.set_current_user(username)
            self.redirect("/")


#--------------------------------------------------------LOGOUT HANDLER------------------------------------------------------------
class LogoutHandler(BaseHandler): 
    def get(self):
        self.clear_cookie("user")
        #self.clear_cookie("country")
        self.redirect(u"/login")


#--------------------------------------------------------ADMIN PAGE------------------------------------------------------------
class CompanyAdminHandler(BaseHandler):
    @tornado.web.addslash
    @tornado.web.authenticated
    def get(self, country=None, page=None):
        if not page:
            self.redirect("/admin/companies/")
            return
        try:
            user = models.Users.objects.get(username=self.current_user)
        except Exception, e:
            logging.info("Could not get user: " + str(e))
            self.redirect("/login/")
        country = user.country
        logging.info("Working in: " + country)
        with open("templates/"+user.country+"/settings.json") as json_file:
            settings = json.load(json_file)
        lan = settings['default_language']
        surveySubmitted = models.Company.objects(Q(submittedSurvey=True) & Q(vetted=True) & Q(country=country)).order_by('prettyName')
        sendSurveys = models.Company.objects(Q(submittedSurvey=False) & Q(country=country))
        needVetting = models.Company.objects(Q(submittedSurvey=True) & Q(vetted=False) & Q(country=country)).order_by('-lastUpdated', 'prettyName')
        try: 
            stats = models.Stats.objects.get(country=country)
        except Exception, e:
            logging.info("Error: " + str(e))
            self.application.stats.create_new_stats(country)
            stats = models.Stats.objects.get(country=country)
        self.render(
            "admin/admin_companies.html",
            page_title='OpenData500',
            page_heading='Admin - ' + country.upper(),
            surveySubmitted = surveySubmitted,
            needVetting = needVetting,
            user=self.current_user,
            country = country,
            sendSurveys = sendSurveys,
            stats = stats,
            settings=settings,
            lan=lan
        )

    def post(self, country=None, page=None):
        try:
            user = models.Users.objects.get(username=self.current_user)
        except Exception, e:
            logging.info("Could not get user: " + str(e))
            self.redirect("/login/")
        action = self.get_argument("action", None)
        country = user.country
        if action == "refresh":
            self.application.stats.refresh_stats(country)
            self.application.files.generate_visit_csv(country)
            stats = models.Stats.objects.get(country=country)
            self.write({"totalCompanies": stats.totalCompanies, 
                        "totalCompaniesWeb":stats.totalCompaniesWeb, 
                        "totalCompaniesSurvey":stats.totalCompaniesSurvey,
                        "totalCompaniesDisplayed": stats.totalCompaniesDisplayed})
        elif action == "files":
            #self.application.files.generate_company_json(country)
            self.application.files.generate_agency_json(country)
            self.application.files.generate_company_csv(country)
            self.application.files.generate_company_all_csv(country)
            self.application.files.generate_agency_csv(country)
            self.write("success")
        elif action == "vizz":
            #self.application.files.generate_sankey_json()
            self.application.files.generate_chord_chart_files(country)
            self.write("success")
        elif action == 'display':
            try:
                id = self.get_argument("id", None)
                c = models.Company.objects.get(id=bson.objectid.ObjectId(id))
            except Exception, e:
                logging.info("Error: " + str(e))
                self.write(str(e))
            c.display = not c.display
            c.save()
            self.application.stats.update_all_state_counts(country)
            self.write("success")
        elif action == 'agency_csv':
            self.application.files.generate_agency_csv(country)
            self.write("success")
        elif action == 'company_csv':
            self.application.files.generate_company_csv(country)
            self.write("success")
        elif action == 'company_all_csv':
            self.application.files.generate_company_all_csv(country)
            self.write("success")
        elif action == "redo_filters":
            self.application.tools.re_do_filters(country)
            self.write("success")


#--------------------------------------------------------ADMIN AGENCIES PAGE------------------------------------------------------------
class AgencyAdminHandler(BaseHandler):
    @tornado.web.addslash
    @tornado.web.authenticated
    def get(self, country=None, page=None):
        try:
            user = models.Users.objects.get(username=self.current_user)
        except Exception, e:
            logging.info("Could not get user: " + str(e))
            self.redirect("/login/")
        country = user.country
        with open("templates/"+user.country+"/settings.json") as json_file:
            settings = json.load(json_file)
        logging.info("Working in: " + country)
        agencies = models.Agency.objects(country=country).order_by('name')
        stats = models.Stats.objects.get(country=country)
        self.render(
            "admin/admin_agencies.html",
            page_title='Admin - Agencies - OpenData500',
            page_heading='Admin - ' + country.upper(),
            user=self.current_user,
            stats = stats,
            agencies=agencies,
            settings=settings,
            country=country,
            lan=settings['default_language']
        )

    @tornado.web.addslash
    @tornado.web.authenticated
    def post(self, country=None, page=None):
        try:
            user = models.Users.objects.get(username=self.current_user)
        except Exception, e:
            logging.info("Could not get user: " + str(e))
            self.redirect("/login/")
        country = user.country
        action = self.get_argument("action", "")
        if action == "agency_list":
            self.application.files.generate_agency_list(country)
            self.write({"message":"All right, I'm done."})
        elif action == "refresh":
            self.application.stats.update_total_agencies(country)
            self.write({"message":"All right, I'm done.", "total_agencies": self.application.stats.get_total_agencies(country)})



#--------------------------------------------------------COMPANY EDIT (ADMIN) PAGE------------------------------------------------------------
class AdminEditCompanyHandler(BaseHandler):
    @tornado.web.addslash
    @tornado.web.authenticated
    def get(self, id):
        try: 
            company = models.Company.objects.get(id=bson.objectid.ObjectId(id))
            page_heading = "Editing " + company.companyName + ' (Admin)'
            page_title = "Editing " + company.companyName + ' (Admin)'
        except Exception, e:
            logging.info('Could not get company: ' + str(e))
            self.redirect('/404/')
        user = models.Users.objects.get(username=self.current_user)
        country=user.country
        with open("templates/"+country+"/settings.json") as json_file:
            settings = json.load(json_file)
        self.render("admin/admin_edit_company.html",
            page_title = page_title,
            page_heading = page_heading,
            company = company,
            companyType = companyType,
            companyFunction = companyFunction,
            criticalDataTypes = criticalDataTypes,
            revenueSource = revenueSource,
            categories=categories,
            datatypes = datatypes,
            stateList = stateList,
            stateListAbbrev=stateListAbbrev,
            user=self.current_user,
            country = company.country,
            country_keys = country_keys,
            id = str(company.id),
            settings = settings,
            lan = settings['default_language']
        )

    @tornado.web.authenticated
    def post(self, id):
        #print all arguments to log:
        logging.info("Admin Editing Company")
        logging.info(self.request.arguments)
        #get user editing and set country
        try:
            user = models.Users.objects.get(username=self.current_user)
        except Exception, e:
            logging.info("Could not get user: " + str(e))
            self.redirect("/login/")
        country = user.country
        logging.info("Working in: " + country)
        #get the company you will be editing
        company = models.Company.objects.get(id=bson.objectid.ObjectId(id))
        #------------------CONTACT INFO-------------------
        company.contact.firstName = self.get_argument("firstName", None)
        company.contact.lastName = self.get_argument("lastName", None)
        company.contact.title = self.get_argument("title", None)
        company.contact.org = self.get_argument("org", None)
        company.contact.email = self.get_argument("email", None)
        company.contact.phone = self.get_argument("phone", None)
        try: 
            if self.request.arguments['contacted']:
                company.contact.contacted = True
        except:
            company.contact.contacted = False
        #------------------CEO INFO-------------------
        company.ceo.firstName = self.get_argument("ceoFirstName", None)
        company.ceo.lastName = self.get_argument("ceoLastName", None)
        #------------------COMPANY INFO-------------------
        company.companyName = self.get_argument("companyName", None)
        company.prettyName = re.sub(r'([^\s\w])+', '', company.companyName).replace(" ", "-").title()
        company.url = self.get_argument('url', None)
        company.city = self.get_argument('city', None)
        company.state = self.get_argument('state', None)
        company.zipCode = self.get_argument('zipCode', None)
        company.companyType = self.get_argument("companyType", None)
        if company.companyType == 'other': #if user entered custom option for Type
            company.companyType = self.get_argument('otherCompanyType', None)
        company.yearFounded = self.get_argument("yearFounded", 0)
        if  not company.yearFounded:
            company.yearFounded = 0
        company.fte = self.get_argument("fte", 0)
        if not company.fte:
            company.fte = 0
        company.companyCategory = self.get_argument("category", None)
        if company.companyCategory == "Other":
            company.companyCategory = self.get_argument("otherCategory", None)
        try: #try and get all checked items. 
            company.revenueSource = self.request.arguments['revenueSource']
        except: #if no checked items, then make it into an empty array (form validation should prevent this always)
            company.revenueSource = []
        if 'Other' in company.revenueSource: #if user entered a custom option for Revenue Source
            del company.revenueSource[company.revenueSource.index('Other')] #delete 'Other' from list
            if self.get_argument('otherRevenueSource', None):
                company.revenueSource.append(self.get_argument('otherRevenueSource', None)) #add custom option to list.
        company.description = self.get_argument('description', None)
        company.descriptionShort = self.get_argument('descriptionShort', None)
        company.financialInfo = self.get_argument('financialInfo', None)
        company.datasetWishList = self.get_argument('datasetWishList', None)
        company.sourceCount = self.get_argument('sourceCount', None) 
        company.dataComments = self.get_argument('dataComments', None)
        company.filters = [company.companyCategory, company.state] #re-do filters
        for a in company.agencies:
                if a.prettyName:
                    company.filters.append(a.prettyName)
        if self.get_argument("submittedSurvey", None) == "submittedSurvey":
            company.submittedSurvey = True
            company.filters.append("survey-company")
        else:
            company.submittedSurvey = False
        if self.get_argument("vettedByCompany", None) == "vettedByCompany":
            company.vettedByCompany = False
        else:
            company.vettedByCompany = True
        if self.get_argument("vetted", None) == "vetted":
            company.vetted = True
        else: 
            company.vetted = False
        if self.get_argument("display", None) == "display":
            company.display = True
        else: 
            company.display = False
        if self.get_argument("locked", None) == "locked":
            company.locked = True
        else: 
            company.locked = False
        company.lastUpdated = datetime.now()
        company.notes = self.get_argument("notes", None)
        company.save()
        self.application.stats.update_all_state_counts(country)
        self.write('success')


#--------------------------------------------------------EDIT COMPANY PAGE------------------------------------------------------------
class EditCompanyHandler(BaseHandler):
    @tornado.web.addslash
    def get(self, country=None, page=None, id=None):
        try: 
            company = models.Company.objects.get(id=bson.objectid.ObjectId(id))
        except Exception, e:
            logging.info("Could not get company: " + str(e))
            self.redirect("/404/")
            return
        if company.country != country:
            self.redirect(str('/'+company.country+'/' + page + '/'+id))
            return
        with open("templates/"+company.country+"/settings.json") as json_file:
            settings = json.load(json_file)
        lan = self.get_cookie('lan')
        if not lan:
            lan = settings['default_language']
        if page == 'edit':
            #non-admin edit
            if not company.locked:
                self.render(company.country + "/" + lan + "/editCompany.html",
                    page_heading = "Editing " + company.companyName,
                    company = company,
                    companyType = companyType,
                    companyFunction = companyFunction,
                    criticalDataTypes = criticalDataTypes,
                    revenueSource = revenueSource,
                    categories=categories,
                    datatypes = datatypes,
                    stateList = stateList,
                    stateListAbbrev=stateListAbbrev,
                    user=self.current_user,
                    country = company.country,
                    country_keys=country_keys,
                    settings = settings,
                    lan=lan,
                    id = str(company.id)
                )
            else:
                self.redirect('/' + company.country + '/locked/')
                return
        if page == 'admin-edit':
            try:
                user = models.Users.objects.get(username=self.current_user)
            except Exception, e:
                logging.info("Could not get user: " + str(e))
                self.redirect("/login/")
            if user.country != company.country:
                logging.info("This user does not have access to edit this company")
                self.redirect('/' + user.country + '/locked/')
                return
            self.render("admin/admin_edit_company.html",
                page_heading = "Editing " + company.companyName + ' (Admin)',
                company = company,
                companyType = companyType,
                companyFunction = companyFunction,
                criticalDataTypes = criticalDataTypes,
                revenueSource = revenueSource,
                categories=categories,
                datatypes = datatypes,
                stateList = stateList,
                stateListAbbrev=stateListAbbrev,
                user=self.current_user,
                country = company.country,
                country_keys = country_keys,
                id = str(company.id),
                settings = settings,
                lan = settings['default_language']
            )

    def post(self, country=None, page=None, id=None):
        logging.info(self.request.arguments)
        form_values = {k:','.join(v) for k,v in self.request.arguments.iteritems()}
        self.application.form.process_company(form_values, id)
        self.write('success')



#--------------------------------------------------------ADD AGENCY (ADMIN) PAGE------------------------------------------------------------
# class AdminAddAgencyHandler(BaseHandler):
#     @tornado.web.addslash
#     @tornado.web.authenticated
#     def get(self):
#         try:
#             user = models.Users.objects.get(username=self.current_user)
#         except Exception, e:
#             logging.info("Could not get user: " + str(e))
#             self.redirect("/login/")
#             return
#         country = user.country
#         with open("templates/"+country+"/settings.json") as json_file:
#             settings = json.load(json_file)
#         self.render(
#             "admin/admin_add_agency.html",
#             page_title='Admin - Edit Agencies - OpenData500',
#             page_heading='Admin - ' + country.upper(),
#             user=self.current_user,
#             country=country,
#             settings=settings,
#             lan=settings['default_language'],
#             agency_types=agency_types
#         )

#--------------------------------------------------------EDIT AGENCY (ADMIN) PAGE------------------------------------------------------------
class AdminEditAgencyHandler(BaseHandler):
    @tornado.web.addslash
    @tornado.web.authenticated
    def get(self, id=None):
        try:
            user = models.Users.objects.get(username=self.current_user)
        except Exception, e:
            logging.info("Could not get user: " + str(e))
            self.redirect("/login/")
            return
        country = user.country
        with open("templates/"+country+"/settings.json") as json_file:
            settings = json.load(json_file)
        if id:
            try:
                agency = models.Agency.objects.get(id=bson.objectid.ObjectId(id))
            except Exception, e:
                logging.info("Could not get agency: " + str(e))
                self.redirect('/404/')
                return
            self.render('admin/admin_edit_agency.html',
                page_heading="Editing " + agency.name,
                page_title="Editing " + agency.name,
                user=self.current_user,
                agency=agency,
                agency_types=agency_types,
                country = agency.country,
                settings=settings,
                lan=settings['default_language']
            )
        else:
            blank_agency = models.Agency(name="", 
                abbrev="", 
                url="", 
                source="", 
                subagencies=[], 
                datasets=[], 
                usedBy=[], 
                notes="", 
                country=country)
            self.render(
            "admin/admin_edit_agency.html",
            page_title='Admin - Edit Agencies - OpenData500',
            page_heading='New Agency',
            user=self.current_user,
            country=country,
            agency=blank_agency,
            agency_types=agency_types,
            settings=settings,
            lan=settings['default_language']
        )

    @tornado.web.authenticated
    def post(self, id):
        try:
            user = models.Users.objects.get(username=self.current_user)
        except Exception, e:
            logging.info("Could not get user: " + str(e))
            self.redirect("/login/")
        country = user.country
        action = self.get_argument("action", "")
        if action != "add-agency":
            try:
                agency = models.Agency.objects.get(id=bson.objectid.ObjectId(id))
            except Exception, e:
                logging.info("Could not get agency: " + str(e))
                self.write({"error":"Agency not found."})
        #logging.info(self.request.arguments)
        subagency_old_name = self.get_argument("subagency_old_name","")
        subagency_new_name = self.get_argument("subagency_new_name", "")
        subagency_abbrev = self.get_argument("subagency_abbrev", "")
        subagency_url = self.get_argument("subagency_url", "")
        agency_new_name = self.get_argument("agency_new_name", "")
        agency_old_name = self.get_argument("agency_old_name", None)
        agency_prettyName = re.sub(r'([^\s\w])+', '', agency_new_name).replace(" ", "-").title()
        agency_abbrev = self.get_argument("agency_abbrev", None)
        agency_url = self.get_argument("agency_url", None)
        agency_type = self.get_argument("agency_type", None)
        agency_source = self.get_argument("agency_source", None)
        agency_notes = self.get_argument("agency_notes", None)
        #------------------------------------------ADD NEW AGENCY----------------------------
        if action == "add-agency":
            new_agency = models.Agency()
            new_agency.name = agency_new_name
            new_agency.prettyName = agency_prettyName
            new_agency.abbrev = agency_abbrev
            new_agency.url = agency_url
            new_agency.dataType = agency_type
            new_agency.source = agency_source
            new_agency.notes = agency_notes
            new_agency.country = country
            new_agency.usedBy_count = 0
            new_agency.usedBy = []
            try:
               new_agency.save()
            except Exception, e:
                logging.info("Could not save agency: " + str(e))
                self.write({"error":"Could not save agency"})
                return
            self.write({"message":"Save Successful", "id":str(new_agency.id)})
            return
        #------------------------------------------EDIT SUBAGENCY----------------------------
        if action =="edit-subagency":
            for s in agency.subagencies:
                if s.name.lower() == subagency_new_name.lower() and s.name.lower() != subagency_old_name.lower():
                    self.write({"message":"Another Subagency already has this name."})
                    return
            for s in agency.subagencies:
                if s.name == subagency_old_name:
                    s.name = subagency_new_name
                    s.abbrev = subagency_abbrev
                    s.url = subagency_url
                    agency.save()
                    self.application.files.generate_agency_list(country)
                    self.write({"message":"Edit Successful"})
                    return 
        #------------------------------------------ADD SUBAGENCY----------------------------
        if action == "add-subagency":
            for s in agency.subagencies:
                if s.name.lower() == subagency_new_name.lower() and s.name.lower() != subagency_old_name.lower():
                    self.write({"message":"Another Subagency already has this name.", "error":""})
                    return
            s = models.Subagency(
                name = subagency_new_name,
                abbrev = subagency_abbrev,
                url = subagency_url)
            agency.subagencies.append(s)
            agency.save()
            self.application.files.generate_agency_list(country)
            self.write({"message":"Subagency added!", 
                "heading":s.name, 
                "name":s.name, 
                "abbrev":s.abbrev, 
                "url":s.url, 
                "new_action":"edit-subagency", 
                "button":"Save Edits", 
                "delete_button":""})
            return
        #------------------------------------------DELETE SUBAGENCY----------------------------
        if action == "delete-subagency":
            logging.info("about to delete")
            for s in agency.subagencies:
                if s.name == subagency_old_name:
                    if len(s.usedBy) != 0:
                        self.write({"message": "Subagency is used by a company or companies; cannot delete.", "error":"error"})
                        return
                    else:
                        agency.subagencies.remove(s)
            agency.save()
            self.application.files.generate_agency_list(country)
            self.write({"message":"Subagency deleted :("})
            return
        #------------------------------------------EDIT AGENCY----------------------------
        if action == "edit-agency":
            if agency_new_name != agency_old_name:
                logging.info("name changed")
                try:
                    agency_exists = models.Agency.objects.get(name=agency_new_name)
                except Exception, e:
                    logging.info("Could not find agency, therefore not duplicate name, carry on: " + str(e))
                    agency_exists = False
                if agency_exists:
                    self.write({"message":"Another agency already has that name, try another."})
                    return
            agency.name = agency_new_name
            agency.prettyName = agency_prettyName
            agency.abbrev = agency_abbrev
            agency.url = agency_url
            agency.dataType = agency_type
            agency.source = agency_source
            agency.notes = agency_notes
            agency.save()
            self.application.files.generate_agency_list(country)
            self.write({"message":"Edits saved!"})
            return
        #------------------------------------------DELETE AGENCY----------------------------
        if action == "delete-agency":
            logging.info(self.request.arguments)
            if agency.subagencies:
                for s in agency.subagencies:
                    if len(s.usedBy) != 0:
                        self.write({"message": "Agency has one or more subagencies used by a company or companies; cannot delete."})
                        return
            if agency.usedBy_count or len(agency.usedBy) !=0:
                self.write({"message": "Agency is used by one or more companies; cannot delete."})
                return
            if agency.usedBy_count == 0 and len(agency.usedBy) == 0:
                agency.delete()
                self.application.files.generate_agency_list(country)
                self.write({"message": "Agency Deleted"})
                return


#--------------------------------------------------------DELETE COMPANY------------------------------------------------------------
class DeleteCompanyHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self, id):
        try:
            company = models.Company.objects.get(id=bson.objectid.ObjectId(id)) 
        except:
            self.render(
                "404.html",
                page_title='404 - Open Data500',
                page_heading='Oh no...',
                error = "404 - Not Found"
            )
        # #-----REMOVE FROM ALL AGENCIES-----
        agencies = models.Agency.objects(usedBy__in=[str(company.id)])
        for a in agencies:
            #-----REMOVE DATASETS (AGENCY)-----
            temp = []
            temp_print = []
            for d in a.datasets:
                if d.usedBy != company:
                    temp.append(d)
                    temp_print.append(d.usedBy.companyName)
            a.datasets = temp
            logging.info(temp_print)
            #---REMOVE DATASETS (SUBAGENCY)---
            for s in a.subagencies:
                temp = []
                temp_print = []
                for d in s.datasets:
                    if company != d.usedBy:
                        temp.append(d)
                        temp_print.append(d.usedBy.companyName)
                s.datasets = temp
                logging.info(temp_print)
                #--REMOVE FROM SUBAGENCIES--
                if company in s.usedBy:
                    s.usedBy.remove(company)
            #-----REMOVE FROM AGENCY----
            a.usedBy.remove(company)
            a.usedBy_count = len(a.usedBy)
            a.save()
        ##----------DELETE COMPANY--------
        company.delete()
        self.redirect('/admin/companies/')













